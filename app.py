from nicegui import ui
from PIL import Image
import bitcoin
import qrcode
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from datetime import datetime
import requests
import mysql.connector, os


# --- Database helpers ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "btcuser"),
        password=os.getenv("DB_PASS", "btcpass"),
        database=os.getenv("DB_NAME", "btcdb"),
    )

def get_address_count():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM public_addresses")
    (count,) = cur.fetchone()
    cur.close()
    conn.close()
    return count

def save_address_to_db(address):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO public_addresses (address) VALUES (%s)", (address,))
    conn.commit()
    cur.close()
    conn.close()


# --- PDF generator ---
def create_pdf_file(private, public):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # HEADER
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 80, "BITCOIN KEYPAIR")
    y = height - 140

    # PUBLIC KEY
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y + 29, "PUBLIC KEY:")
    qr_pub = qrcode.QRCode(border=1)
    qr_pub.add_data(public)
    qr_pub.make(fit=True)
    qr_pub = qr_pub.make_image(fill_color="black", back_color="white")
    buf_pub = io.BytesIO()
    qr_pub.save(buf_pub, format="PNG")
    buf_pub.seek(0)
    c.drawImage(ImageReader(buf_pub), 180, y - 230, width=250, height=250)

    text_obj = c.beginText(200, y - 250)
    text_obj.setFont("Helvetica-Bold", 10)
    text_obj.setFillColor(colors.black)
    for line in [public[i:i + 70] for i in range(0, len(public), 70)]:
        text_obj.textLine(line)
    c.drawText(text_obj)

    y -= 260

    # PRIVATE KEY
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y - 20, "PRIVATE KEY:")
    y -= 25
    qr_priv = qrcode.QRCode(border=1)
    qr_priv.add_data(private)
    qr_priv.make(fit=True)
    qr_priv = qr_priv.make_image(fill_color="black", back_color="white")
    buf_priv = io.BytesIO()
    qr_priv.save(buf_priv, format="PNG")
    buf_priv.seek(0)
    c.drawImage(ImageReader(buf_priv), 180, (y - 20) - 230, width=250, height=250)

    text_obj = c.beginText(132, (y - 20) - 250)
    text_obj.setFont("Helvetica-Bold", 10)
    text_obj.setFillColor(colors.black)
    for line in [private[i:i + 70] for i in range(0, len(private), 70)]:
        text_obj.textLine(line)
    c.drawText(text_obj)

    # FOOTER
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 100, "BITCOIN account holder: _____________________________________________")
    c.setFont("Helvetica-Oblique", 10)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.drawString(50, 80, f"Generated on: {timestamp}")
    c.save()
    buffer.seek(0)
    return buffer.read()


# --- UI Page: Home ---
@ui.page('/')
def page():
    # Placeholders
    public_key_text = None
    private_key_text = None
    public_qr_ui = None
    private_qr_ui = None
    balance_label = None
    balance_link_html = None
    counter_label = None
    current_private = None
    current_public = None
    download_in_progress = False

    # --- helpers ---
    def update_counter():
        nonlocal counter_label
        counter_label.text = f"Total Addresses Generated: {get_address_count()}"

    def generate_keys():
        nonlocal current_private, current_public
        current_private = bitcoin.random_key()
        current_public = bitcoin.pubtoaddr(bitcoin.privtopub(current_private))

        save_address_to_db(current_public)

        # Update labels
        public_key_text.text = f'Public Key: {current_public}'
        private_key_text.text = f'Private Key: {current_private}'

        # Update QR codes
        buf_pub = io.BytesIO()
        qrcode.make(current_public).save(buf_pub, format='PNG')
        buf_pub.seek(0)
        public_qr_ui.set_source(f"data:image/png;base64,{base64.b64encode(buf_pub.read()).decode()}")

        buf_priv = io.BytesIO()
        qrcode.make(current_private).save(buf_priv, format='PNG')
        buf_priv.seek(0)
        private_qr_ui.set_source(f"data:image/png;base64,{base64.b64encode(buf_priv.read()).decode()}")

        # Reset balance
        balance_label.text = 'Balance: Not checked'

        # Update external link
        balance_link_html.content = (
            f'<a href="https://www.blockchain.com/btc/address/{current_public}" '
            f'target="_blank" style="color:blue; text-decoration:underline;">'
            f'🔗 View on Blockchain.com</a>'
        )
        balance_link_html.visible = True
        balance_link_html.update()

        # Update counter
        update_counter()

    def check_balance():
        nonlocal current_public
        if not current_public:
            ui.notify('Generate keys first!')
            return
        try:
            url = f"https://blockchain.info/balance?active={current_public}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if current_public in data:
                    final_balance_sat = data[current_public]['final_balance']
                    balance_btc = final_balance_sat / 1e8
                    balance_label.text = f'Balance: {balance_btc:.8f} BTC'
                else:
                    balance_label.text = 'Balance: Address not found'
                    ui.notify('Address not found on blockchain.', color='negative')
            else:
                balance_label.text = 'Balance: API Error'
                ui.notify(f'API error: {response.status_code}', color='negative')
        except requests.exceptions.RequestException as e:
            balance_label.text = 'Balance: Network Error'
            ui.notify(f'Network error: {str(e)}', color='negative')
        except Exception as e:
            balance_label.text = 'Balance: Unknown Error'
            ui.notify(f'Unexpected error: {str(e)}', color='negative')

    def download_pdf():
        nonlocal download_in_progress
        if download_in_progress:
            return
        if current_private and current_public:
            download_in_progress = True
            pdf_bytes = create_pdf_file(current_private, current_public)
            timestamp_1 = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            ui.download(pdf_bytes, filename=f"bitcoin_keys_{timestamp_1}.pdf")
            download_in_progress = False
        else:
            ui.notify('Generate keys first!')

    # --- UI Layout ---
    ui.label('Bitcoin Private Key Generator').classes('text-2xl font-bold mb-6')
    with ui.row().classes('mb-6'):
        ui.button('Generate Keys', on_click=generate_keys)
        ui.button('Check Balance', on_click=check_balance).classes('bg-blue-500 text-white')
        ui.button('Download PDF', on_click=download_pdf)

    public_key_text = ui.label('Public Key: —').classes('text-sm mb-2 break-all')
    private_key_text = ui.label('Private Key: —').classes('text-sm mb-4 break-all')

    balance_label = ui.label('Balance: Not checked').classes('text-lg mb-2 font-semibold text-green-600')

    balance_link_html = ui.html('').style(
        'font-size:12px; padding:4px; border:1px solid #ccc; border-radius:4px;'
    )
    balance_link_html.visible = False

    with ui.row().classes('mb-6'):
        with ui.column().classes('items-center'):
            public_qr_ui = ui.image().style('width:220px; height:220px;').classes('border border-gray-400 p-2')
            ui.label('Public Key').classes('mt-2 text-center')
        with ui.column().classes('items-center'):
            private_qr_ui = ui.image().style('width:220px; height:220px;').classes('border border-gray-400 p-2')
            ui.label('Private Key').classes('mt-2 text-center')

    # Counter label
    counter_label = ui.label('').classes('text-lg mt-4')
    update_counter()

    # Redirect to history page
    ui.button('Show History', on_click=lambda: ui.navigate.to('/history')).classes('bg-gray-500 text-white mt-4')


# --- UI Page: History ---
@ui.page('/history')
def history_page():
    ui.label('Address History (latest first)').classes('text-2xl font-bold mb-6')

    columns = [
        {'name': 'id', 'label': 'ID', 'field': 'id'},
        {'name': 'address', 'label': 'Public Address', 'field': 'address'},
        {'name': 'generated_at', 'label': 'Generated At', 'field': 'generated_at'},
    ]

    table = ui.table(columns=columns, rows=[]).classes('w-full')

    def load_page(page_number: int = 0):
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)  # fetch as dicts
        cur.execute("""
            SELECT id, address, generated_at
            FROM public_addresses
            ORDER BY generated_at ASC
            LIMIT 100 OFFSET %s
        """, (page_number * 100,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        table.rows = rows

    # pagination
    page_number = 0

    def go_prev():
        nonlocal page_number
        if page_number > 0:
            page_number -= 1
            load_page(page_number)

    def go_next():
        nonlocal page_number
        page_number += 1
        load_page(page_number)

    with ui.row().classes('mt-4'):
        ui.button('Previous', on_click=go_prev)
        ui.button('Next', on_click=go_next)
        ui.button('Back to Home', on_click=lambda: ui.navigate.to('/'))

    load_page(0)


# --- Run App ---
ui.run(title='Bitcoin Private Key Generator', port=8080)
