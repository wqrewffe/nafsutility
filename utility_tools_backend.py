from flask import Flask, request, jsonify
from flask_cors import CORS
from io import BytesIO
from PIL import Image
import base64, secrets, string, zipfile, qrcode
from reportlab.pdfgen import canvas

app = Flask(__name__)
CORS(app)

def b64_to_bytes(data_b64: str) -> bytes:
    header_sep = data_b64.find(',')
    if header_sep != -1:
        data_b64 = data_b64[header_sep+1:]
    return base64.b64decode(data_b64)

def bytes_to_b64(data: bytes, mime: str = 'application/octet-stream') -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode('utf-8')

@app.route('/api/utility/password', methods=['POST'])
def generate_password():
    body = request.get_json() or {}
    length = int(body.get('length', 16))
    use_upper = bool(body.get('use_upper', True))
    use_digits = bool(body.get('use_digits', True))
    use_symbols = bool(body.get('use_symbols', True))

    alphabet = string.ascii_lowercase
    if use_upper:
        alphabet += string.ascii_uppercase
    if use_digits:
        alphabet += string.digits
    if use_symbols:
        alphabet += '!@#$%^&*()-_=+[]{};:,.<>?'

    password = ''.join(secrets.choice(alphabet) for _ in range(max(4, length)))
    return jsonify({'password': password})

@app.route('/api/utility/resize', methods=['POST'])
def resize_image():
    body = request.get_json() or {}
    img_b64 = body.get('image_base64')
    width = int(body.get('width', 800))
    height = int(body.get('height', 600))

    if not img_b64:
        return jsonify({'error': 'image_base64 required'}), 400

    try:
        img_data = b64_to_bytes(img_b64)
        img = Image.open(BytesIO(img_data)).convert('RGBA')
        img = img.resize((width, height), Image.LANCZOS)
        out = BytesIO()
        img.save(out, format='PNG')
        out.seek(0)
        return jsonify({'image_base64': bytes_to_b64(out.read(), 'image/png')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/utility/convert', methods=['POST'])
def convert_text_to_pdf():
    body = request.get_json() or {}
    text = body.get('text', '')
    if not text:
        return jsonify({'error': 'text required'}), 400

    out = BytesIO()
    p = canvas.Canvas(out)
    width, height = p._pagesize
    margin = 40
    y = height - margin
    line_height = 12

    for line in text.split('\n'):
        if y < margin:
            p.showPage()
            y = height - margin
        p.drawString(margin, y, line[:200])
        y -= line_height

    p.save()
    out.seek(0)
    pdf_base64 = bytes_to_b64(out.read(), 'application/pdf')
    return jsonify({'pdf_base64': pdf_base64})

@app.route('/api/utility/compress', methods=['POST'])
def compress_files():
    body = request.get_json() or {}
    files = body.get('files', [])
    if not files:
        return jsonify({'error': 'files required'}), 400

    out = BytesIO()
    with zipfile.ZipFile(out, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            name = f.get('name', 'file')
            data_b64 = f.get('data_base64')
            if not data_b64:
                continue
            zf.writestr(name, b64_to_bytes(data_b64))
    out.seek(0)
    return jsonify({'zip_base64': bytes_to_b64(out.read(), 'application/zip')})

@app.route('/api/utility/qrcode', methods=['POST'])
def generate_qrcode():
    body = request.get_json() or {}
    text = body.get('text', '')
    size = int(body.get('size', 256))
    if not text:
        return jsonify({'error': 'text required'}), 400

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    img = img.resize((size, size))
    out = BytesIO()
    img.save(out, format='PNG')
    out.seek(0)
    return jsonify({'qrcode_base64': bytes_to_b64(out.read(), 'image/png')})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
