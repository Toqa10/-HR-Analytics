import os

import zipfile
import subprocess
import platform

def compress_to_zip(input_file, output_file=None):
    """ضغط الملف إلى ZIP"""
    if not output_file:
        output_file = os.path.splitext(input_file)[0] + '.zip'
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(input_file, os.path.basename(input_file))
    print(f"تم إنشاء {output_file} بنجاح (ZIP)")

def compress_to_rar(input_file, output_file=None):
    """ضغط الملف إلى RAR (يحتاج WinRAR أو RAR مثبت في PATH على Windows)"""
    if not output_file:
        output_file = os.path.splitext(input_file)[0] + '.rar'
    
    system = platform.system()
    if system == "Windows":
        # الأمر يعمل إذا كان WinRAR موجود في PATH
        cmd = f'WinRAR a -ep1 "{output_file}" "{input_file}"'
        subprocess.run(cmd, shell=True)
        print(f"تم إنشاء {output_file} بنجاح (RAR)")
    else:
        print("ضغط RAR على Linux/Mac يحتاج تثبيت rar/rarfile")

# مثال الاستخدام
input_csv = "salary.csv"

# ضغط إلى ZIP
compress_to_zip(input_csv)

# ضغط إلى RAR (Windows فقط)
compress_to_rar(input_csv)
