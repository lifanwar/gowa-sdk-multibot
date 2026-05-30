from utils.timestamp_parser import parse_timestamp
from utils.number_parser import parse_number
from utils.spreadsheet_connect import get_google_sheet

# ======================#
#       HANDLING        #
# ======================#

async def handle_confirmed_transfer_reply(client, message, text) -> None:
    try:
        sent = await client.reply_message("processing...", message)
        transfer_data = parse_confirmed_transfer_data(text, message)
        hasil_rate = rate_calculation(transfer_data["idr"], transfer_data["rate"])
        
        # Save data        
        save_all_confirmed_transfer_data(transfer_data, hasil_rate, message)

        await client.update_message(
            message_id=sent["message_id"],
            to=message.contact_id,
            text=(
                f"✅ Done\n"
                f"Total EGP: {hasil_rate:,.0f}"
            ).replace(",", "."),
        )

    except Exception as e:
        print(f"Failed to save confirmed transfer: {e}")

        if sent:
            await client.update_message(
                message_id=sent["message_id"],
                to=message.contact_id,
                text="❌ Gagal Input Data",
            )
        else:
            await client.reply_message("❌ Gagal Input Data", message)

# ======================#
#         UTILS         #
# ======================#

# PARSER DATA
def parse_confirmed_transfer_data(text: str, message) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    timestamp = parse_timestamp(message.raw.get("timestamp"))
    customer = message.chat_id.split("@", 1)[0] if message.chat_id else None

    data = {
        "type": lines[0] if lines else None,
        "idr": None,
        "rate": None,
        "to": None,
        "from": None,
        "date": timestamp.get("date"),
        "customer": customer
    }

    for line in lines[1:]:
        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        normalized_key = key.strip().lower()
        value = value.strip()

        if normalized_key == "idr":
            data["idr"] = parse_number(value)
        elif normalized_key == "rate":
            data["rate"] = value
        elif normalized_key == "to":
            data["to"] = value
        elif normalized_key == "from":
            data["from"] = value

    return data

# CALLING SAVE DATA TO SHEET
def save_all_confirmed_transfer_data(data: dict, hasil_rate: int, message) -> None:
    try:
        save_confirmed_transfer_to_sheet(data)
    except Exception as e:
        raise Exception(f"Gagal input sheet Transaksi: {e}")

    try:
        save_customer_to_sheet(data, hasil_rate, message)
    except Exception as e:
        raise Exception(f"Gagal input sheet Customers: {e}")
    
def save_confirmed_transfer_to_sheet(data: dict) -> int:
    worksheet = get_google_sheet("Transaksi")

    tanggal = data.get("date")
    idr = data.get("idr")
    rate = data.get("rate")
    wallet_idr_masuk = data.get("to")
    admin_egp_keluar = data.get("from")

    if not tanggal:
        raise ValueError("Tanggal tidak ditemukan")

    if idr is None:
        raise ValueError("IDR tidak ditemukan")

    if not rate:
        raise ValueError("Rate tidak ditemukan")

    # Cek baris kosong berikutnya berdasarkan kolom B
    next_row = len(worksheet.col_values(2)) + 1

    updates = [
        {
            "range": f"B{next_row}",
            "values": [[tanggal]]
        },
        {
            "range": f"C{next_row}",
            "values": [["JUAL"]]
        },
        {
            "range": f"D{next_row}",
            "values": [[f"Jual EGP: Rp{idr:,}, rate {rate}".replace(",", ".")]]
        },
        {
            "range": f"E{next_row}",
            "values": [[1]]
        },
        {
            "range": f"F{next_row}",
            "values": [[idr]]
        },
        {
            "range": f"H{next_row}",
            "values": [[rate]]
        },
        {
            "range": f"Z{next_row}",
            "values": [[wallet_idr_masuk]]
        },
        {
            "range": f"AF{next_row}",
            "values": [[admin_egp_keluar]]
        }
    ]

    worksheet.batch_update(
        updates,
        value_input_option="USER_ENTERED"
    )

    return next_row

def save_customer_to_sheet(data: dict, hasil_rate: float, message) -> int:
    worksheet = get_google_sheet("Customers")

    tanggal = data.get("date")
    customer = message.chat_id.split("@", 1)[0] if message.chat_id else None
    idr = data.get("idr")
    rate = data.get("rate")

    if not tanggal:
        raise ValueError("Tanggal tidak ditemukan")

    if not customer:
        raise ValueError("Customer tidak ditemukan")

    if idr is None:
        raise ValueError("IDR tidak ditemukan")

    if not rate:
        raise ValueError("Rate tidak ditemukan")

    # Karena row 1 adalah header, data mulai dari row 2
    next_row = len(worksheet.col_values(1)) + 1

    if next_row < 2:
        next_row = 2

    customer_id = next_row - 1

    updates = [
        {
            "range": f"A{next_row}",
            "values": [[customer_id]]
        },
        {
            "range": f"B{next_row}",
            "values": [[tanggal]]
        },
        {
            "range": f"C{next_row}",
            "values": [[customer]]
        },
        {
            "range": f"D{next_row}",
            "values": [[idr]]
        },
        {
            "range": f"E{next_row}",
            "values": [[rate]]
        },
        {
            "range": f"F{next_row}",
            "values": [[hasil_rate]]
        }
    ]

    worksheet.batch_update(
        updates,
        value_input_option="USER_ENTERED"
    )

    return next_row

def rate_calculation(idr: int, rate) -> float:
    if idr is None:
        raise ValueError("IDR tidak ditemukan")

    if rate is None:
        raise ValueError("Rate tidak ditemukan")

    rate = float(str(rate).replace(".", "").replace(",", ".").strip())

    result = idr / 1_000_000 * rate

    return result
