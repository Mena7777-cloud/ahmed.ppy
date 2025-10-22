import streamlit as st
from sqlalchemy import or_
from database import SessionLocal, Product, User, Transaction, AuditLog, create_db_and_users, verify_password
from streamlit_option_menu import option_menu
import pandas as pd
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="نظام إدارة التخزين الذكي", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .main { background-color: #F0F2F6; }
    .card { background-color: white; border-radius: 15px; padding: 25px; margin-bottom: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
    h1, h2 { color: #1A237E; }
    .st-emotion-cache-1avcm0n { flex-direction: row-reverse; }
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
    st.title("🧠 نظام إدارة التخزين الذكي")
    _, col, _ = st.columns([1, 1.5, 1])
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

# --- لوحة التحكم ---
if selected_tab == "📊 لوحة التحكم":
    st.header("📊 لوحة التحكم الرئيسية")
    c1, c2, c3 = st.columns(3)
    total_products = db.query(Product).count()
    total_quantity = sum([p.quantity for p in db.query(Product).all()])
    total_value = sum([p.quantity * p.price for p in db.query(Product).all()])
        
    with c1:
        st.markdown(f'<div class="card"><h3>إجمالي أنواع المنتجات</h3><h2>{total_products}</h2></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card"><h3>إجمالي عدد القطع</h3><h2>{total_quantity}</h2></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="card"><h3>القيمة الإجمالية للتخزين</h3><h2>{total_value} جنيه</h2></div>', unsafe_allow_html=True)

# --- إدارة التخزين ---
elif selected_tab == "🗃️ إدارة التخزين":
    st.header("🗃️ إدارة التخزين")
    if st.session_state.user.role == 'admin':
        with st.expander("➕ لإضافة منتج جديد، اضغط هنا", expanded=False):
            with st.form("add_form", clear_on_submit=True):
                st.subheader("بيانات المنتج الأساسية")
                name = st.text_input("اسم المنتج*")
                description = st.text_area("وصف المنتج")
                category = st.text_input("الفئة (مثال: مستلزمات ورقية)")
                supplier = st.text_input("المورّد")
                st.subheader("بيانات التخزين")
                quantity = st.number_input("الكمية الحالية", min_value=0, step=1)
                price = st.number_input("سعر الوحدة (بالجنيه)", min_value=0)
                reorder_level = st.number_input("حد إعادة الطلب", min_value=0, step=1, value=5)
                    
                submitted = st.form_submit_button("💾 إضافة المنتج")
                if submitted and name:
                    new_product = Product(name=name, description=description, category=category, supplier=supplier, quantity=quantity, price=price, reorder_level=reorder_level)
                    db.add(new_product)
                    log_action(st.session_state.user, "إضافة منتج جديد", f"اسم المنتج: {name}")
                    db.commit()
                    st.success("🎉 تم إضافة المنتج بنجاح!")
                    st.balloons()
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 قائمة المنتجات الحالية")
    search_term = st.text_input("🔍 ابحث عن منتج بالاسم أو الفئة...")
        
    query = db.query(Product)
    if search_term:
        query = query.filter(or_(Product.name.contains(search_term), Product.category.contains(search_term)))
        
    all_products = query.order_by(Product.id.desc()).all()

    if not all_products:
        st.warning("لا توجد منتجات تطابق بحثك أو لم يتم إضافة منتجات بعد.")
    else:
        for p in all_products:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader(f"🏷️ {p.name}")
            c1, c2, c3 = st.columns(3)
            c1.info(f"**الكمية الحالية:** {p.quantity}")
            c2.success(f"**السعر:** {p.price} جنيه")
            c3.warning(f"**حد إعادة الطلب:** {p.reorder_level}")
                
            if st.session_state.user.role == 'admin':
                with st.expander("⚙️ الإجراءات (تعديل، حذف، حركات)"):
                    # ... (هنا نضيف أكواد التعديل والحذف والحركات)
                    st.write("قيد التطوير...") # سنضيفها لاحقاً
            st.markdown('</div>', unsafe_allow_html=True)

# --- التنبيهات ---
elif selected_tab == "🔔 التنبيهات":
    st.header("🔔 تنبيهات الأصناف التي تحتاج لإعادة طلب")
    low_stock_products = db.query(Product).filter(Product.quantity <= Product.reorder_level).all()
    if not low_stock_products:
        st.success("✅ كل الأصناف كمياتها ممتازة ولا تحتاج لإعادة طلب حالياً.")
    else:
        for p in low_stock_products:
            st.error(f"**تحذير:** منتج '{p.name}' وصل للحد الأدنى. الكمية الحالية: **{p.quantity}**، وحد إعادة الطلب: **{p.reorder_level}**.")

# --- السجلات ---
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
        if not transactions:
            st.warning("لم يتم تسجيل أي حركات على المنتجات بعد.")
        else:
            for t in transactions:
                user = db.query(User).filter(User.id == t.user_id).first()
                color = "green" if t.type == "إدخال" else "red"
                st.markdown(f"<p style='color:{color};'>**المنتج:** {t.product.name} | **النوع:** {t.type} | **الكمية:** {t.quantity_change} | **السبب:** {t.reason} | **بواسطة:** {user.username if user else 'N/A'} | **الوقت:** {t.timestamp.strftime('%Y-%m-%d %H:%M')}</p>", unsafe_allow_html=True)

db.close()
