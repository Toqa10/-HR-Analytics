import os
import zipfile
import streamlit as st

# عنوان التطبيق
st.title("CSV to ZIP Compressor 💾")

# رفع ملف CSV
uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

if uploaded_file is not None:
    # حفظ الملف مؤقتًا
    temp_file_path = os.path.join("temp.csv")
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"File {uploaded_file.name} uploaded successfully!")

    # اسم ملف ZIP الناتج
    zip_file_name = uploaded_file.name.replace(".csv", ".zip")

    # ضغط الملف
    with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(temp_file_path, os.path.basename(temp_file_path))
    
    st.success(f"File compressed successfully as {zip_file_name}!")

    # رابط لتحميل ملف ZIP
    with open(zip_file_name, "rb") as f:
        st.download_button(
            label="Download ZIP",
            data=f,
            file_name=zip_file_name,
            mime="application/zip"
        )

    # تنظيف الملف المؤقت
    os.remove(temp_file_path)
