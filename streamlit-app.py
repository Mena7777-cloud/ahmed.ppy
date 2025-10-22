import streamlit as st
from sqlalchemy import or_
from database import SessionLocal, Product, User, Transaction, AuditLog, create_db_and_users, verify_password
from streamlit_option_menu import option_menu
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="نظام الرقابة الذكي", page_icon="👁️", layout="wide")

st.markdown("""
<style>
    .main { background-color: #F0F2F6; }
    .card { background-color: white; border-radius: 15px; padding: 25px; margin-bottom: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
    h1 { color: #1A237E; text-align: center; }
</style>
""", unsafe_allow_html=True)

create_db_and_users()
db = SessionLocal()

def log_action(user, action, details=""):
    log = AuditLog(user_id=user.id if user else None, username=user.username if user else "Anonymous", action=action, details=details)
    db.add(log)
    db.commit()

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("👁️ نظام الرقابة الذكي للتخزين")
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.container():
            st.header("🔐 تسجيل الدخول")
            with st.form("login_form"):
                username = st.text_input("👤 اسم المستخدم")
                password = st.text_input("🔑 كلمة المرور", type="password")
                submitted = st.form_submit_button("➡️ تسجيل الدخول")
                if submitted:
                    user_in_db = db.query(User).filter(User.username == username).first()
                    if user_in_db and verify_password(password, user_in_db.password_hash):
                        st.session_state.user = user_in_db
                        log_action(user_in_db, "تسجيل دخول ناجح")
                        st.rerun()
                    else:
                        log_action(None, "محاولة تسجيل دخول فاشلة", f"اسم المستخدم: {username}")
                        st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

with st.sidebar:
    st.title(f"مرحباً, {st.session_state.user.username.capitalize()}")
    st.write(f"**الصلاحيات:** {'👑 مدير' if st.session_state.user.role == 'admin' else '👤 مستخدم'}")
        
    options = ["📊 لوحة التحكم", "🗃️ إدارة التخزين", "🔔 التنبيهات", "📜 السجلات"]
    icons = ["bar-chart-line-fill", "box-seam-fill", "bell-fill", "journal-text"]
    if st.session_state.user.role != 'admin':
        options.remove("📜 السجلات")
        icons.remove("journal-text")

    selected_tab = option_menu(menu_title="القائمة الرئيسية", options=options, icons=icons, menu_icon="list-task", default_index=0)
        
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج"):
        log_action(st.session_state.user, "تسجيل الخروج")
        st.session_state.user = None
        st.rerun()

if selected_tab == "🗃️ إدارة التخزين":
    st.header("🗃️ إدارة التخزين")
    if st.session_state.user.role == 'admin':
        with st.expander("➕ لإضافة منتج جديد، اضغط هنا", expanded=False):
            with st.form("add_form", clear_on_submit=True):
                name = st.text_input("اسم المنتج*")
                # ... (باقي حقول الإضافة)
                submitted = st.form_submit_button("💾 إضافة المنتج")
                if submitted and name:
                    new_product = Product(name=name) # أكمل باقي الحقول
                    db.add(new_product)
                    log_action(st.session_state.user, "إضافة منتج جديد", f"اسم المنتج: {name}")
                    db.commit()
                    st.success("🎉 تم إضافة المنتج بنجاح!")
                    st.rerun()

    all_products = db.query(Product).order_by(Product.id.desc()).all()
    for p in all_products:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader(f"🏷️ {p.name}")
        c1, c2, c3 = st.columns(3)
        c1.info(f"**الكمية الحالية:** {p.quantity}")
        c2.success(f"**السعر:** {p.price} جنيه")
        c3.warning(f"**حد إعادة الطلب:** {p.reorder_level}")
            
        if st.session_state.user.role == 'admin':
            with st.expander("🔄 إجراء حركة على المنتج"):
                with st.form(key=f"trans_{p.id}", clear_on_submit=True):
                    trans_type = st.selectbox("نوع الحركة", ["إدخال", "إخراج"], key=f"type_{p.id}")
                    trans_qty = st.number_input("الكمية", min_value=1, step=1, key=f"qty_{p.id}")
                    trans_reason = st.text_input("السبب (مثال: 'شحنة جديدة', 'بيع لعميل')", key=f"reason_{p.id}")
                        
                    if st.form_submit_button("✔️ تنفيذ الحركة"):
                        if trans_type == "إخراج" and trans_qty > p.quantity:
                            st.error("لا يمكن إخراج كمية أكبر من الموجودة في المخزن!")
                        else:
                            new_trans = Transaction(product_id=p.id, user_id=st.session_state.user.id, type=trans_type, quantity_change=trans_qty, reason=trans_reason)
                            db.add(new_trans)
                                
                            if trans_type == "إدخال":
                                p.quantity += trans_qty
                            else:
                                p.quantity -= trans_qty
                                
                            log_action(st.session_state.user, f"إجراء حركة '{trans_type}'", f"المنتج: {p.name}, الكمية: {trans_qty}, السبب: {trans_reason}")
                                
                            db.commit()
                            st.success("✅ تم تنفيذ الحركة بنجاح!")
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif selected_tab == "📜 السجلات":
    st.header("📜 عرض السجلات")
    log_type = st.selectbox("اختر نوع السجل لعرضه", ["سجل تدقيق النظام (من دخل وخرج)", "سجل حركات المنتجات"])

    if log_type == "سجل تدقيق النظام (من دخل وخرج)":
        st.subheader("سجل تدقيق النظام")
        logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
        for log in logs:
            st.info(f"**المستخدم:** {log.username} | **الحركة:** {log.action} | **التفاصيل:** {log.details} | **الوقت:** {log.timestamp.strftime('%Y-%m-%d %H:%M')}")

    elif log_type == "سجل حركات المنتجات":
        st.subheader("سجل حركات المنتجات")
        transactions = db.query(Transaction).order_by(Transaction.id.desc()).limit(100).all()
        for t in transactions:
            user = db.query(User).filter(User.id == t.user_id).first()
            color = "green" if t.type == "إدخال" else "red"
            st.markdown(f"<p style='color:{color};'>**المنتج:** {t.product.name} | **النوع:** {t.type} | **الكمية:** {t.quantity_change} | **السبب:** {t.reason} | **بواسطة:** {user.username if user else 'N/A'} | **الوقت:** {t.timestamp.strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

# ... (باقي الأقسام مثل لوحة التحكم والتنبيهات كما هي) ...

db.close()
