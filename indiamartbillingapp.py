import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import base64
import urllib.parse
import io
from fpdf import FPDF

# DATABASE INITIALIZATION
def init_db():
    conn = sqlite3.connect("billing.db")
    c = conn.cursor()

    # Table for products
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    price REAL
                )''')

    # Table for bills
    c.execute('''CREATE TABLE IF NOT EXISTS bills (
                    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT,
                    phone TEXT,
                    address TEXT,
                    bill_date TEXT,
                    items TEXT,
                    total REAL
                )''')
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect("billing.db")


# PRODUCT FUNCTIONS
def get_products():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT name, price FROM products ORDER BY name ASC")
    data = c.fetchall()
    conn.close()
    return data

def add_product(name, price):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
        conn.commit()
    except:
        pass
    conn.close()

def update_product_price(name, price):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE products SET price=? WHERE name=?", (price, name))
    conn.commit()
    conn.close()

def delete_product(name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE name=?", (name,))
    conn.commit()
    conn.close()


# BILL FUNCTIONS
def save_bill(cust_name, phone, address, items, total):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO bills (customer_name, phone, address, bill_date, items, total) VALUES (?, ?, ?, ?, ?, ?)",
              (cust_name, phone, address, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(items), total))
    conn.commit()
    conn.close()

def search_bills(query):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM bills WHERE customer_name LIKE ? OR phone LIKE ?", (f"%{query}%", f"%{query}%"))
    rows = c.fetchall()
    conn.close()
    return rows


# STREAMLIT UI
st.set_page_config(page_title="INDIA ELECTRONICS MART", layout="wide")
st.title("🇮🇳 INDIA ELECTRONICS MART")

init_db()

menu = ["Billing", "Manage Products", "Search Bills"]
choice = st.sidebar.selectbox("Menu", menu)

if "cart" not in st.session_state:
    st.session_state.cart = []


# MANAGE PRODUCTS
if choice == "Manage Products":
    st.subheader("Manage Products")

    col1, col2 = st.columns(2)
    with col1:
        pname = st.text_input("Product Name")
        pprice = st.number_input("Price", min_value=0.0, step=0.01, format="%.2f")
        if st.button("Add Product"):
            add_product(pname, pprice)
            st.success(f"Added product: {pname}")

    with col2:
        products = get_products()
        if products:
            product_names = [p[0] for p in products]
            selected = st.selectbox("Select Product to Update/Delete", product_names)
            new_price = st.number_input("Update Price", min_value=0.0, step=0.01, format="%.2f")
            if st.button("Update Price"):
                update_product_price(selected, new_price)
                st.success("Price updated")
            if st.button("Delete Product"):
                delete_product(selected)
                st.warning("Product deleted")

    st.write("### Current Product List")
    df_products = pd.DataFrame(products, columns=["Product", "Price"])
    st.dataframe(df_products)


# BILLING PAGE
elif choice == "Billing":
    st.subheader("Create Bill")
    col1, col2, col3 = st.columns(3)
    with col1:
        cust_name = st.text_input("Customer Name")
    with col2:
        phone = st.text_input("Phone Number (with country code, e.g. +91XXXXXXXXXX)")
    with col3:
        address = st.text_input("Address")

    products = get_products()
    if products:
        prod_names = [p[0] for p in products]
        selected_product = st.selectbox("Select Product", prod_names)
        qty = st.number_input("Quantity", 1, 100, 1)
        discount = st.number_input("Discount (%)", 0, 100, 0)
        gst = st.number_input("GST (%)", 0, 50, 0)

        if st.button("Add to Cart"):
            price = dict(products)[selected_product]
            st.session_state.cart.append({
                "product": selected_product,
                "price": price,
                "qty": qty,
                "discount": discount,
                "gst": gst
            })

        if st.button("Clear Cart"):
            st.session_state.cart = []

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        df_cart["Total"] = df_cart.apply(lambda x: (x["price"] * x["qty"]) * (1 - x["discount"]/100) * (1 + x["gst"]/100), axis=1)
        st.write("### Cart Items")
        st.dataframe(df_cart)
        grand_total = df_cart["Total"].sum()
        st.subheader(f"Grand Total: ₹{grand_total:.2f}")

        if st.button("Generate Bill"):
            save_bill(cust_name, phone, address, st.session_state.cart, grand_total)
            st.success("Bill Generated and Saved!")

            # Create PDF Invoice
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=16)
            pdf.cell(200, 10, txt="INDIA ELECTRONICS MART", ln=True, align="C")
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 8, txt=f"Customer: {cust_name}", ln=True)
            pdf.cell(200, 8, txt=f"Phone: {phone}", ln=True)
            pdf.cell(200, 8, txt=f"Address: {address}", ln=True)
            pdf.cell(200, 8, txt=f"Date: {datetime.now()}", ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            pdf.cell(60, 8, "Product", 1)
            pdf.cell(30, 8, "Qty", 1)
            pdf.cell(40, 8, "Price", 1)
            pdf.cell(40, 8, "Total", 1, ln=True)

            for _, row in df_cart.iterrows():
                pdf.cell(60, 8, row['product'], 1)
                pdf.cell(30, 8, str(row['qty']), 1)
                pdf.cell(40, 8, f"Rs.{row['price']:.2f}", 1)
                pdf.cell(40, 8, f"Rs.{row['price']:.2f}", 1, ln=True)

            pdf.cell(130, 8, "Grand Total", 1)
            pdf.cell(40, 8, f"Rs.{grand_total:.2f}", 1, ln=True)

            pdf_output = "invoice.pdf"
            pdf.output(pdf_output)

            # Create download link
            with open(pdf_output, "rb") as f:
                pdf_bytes = f.read()
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="invoice.pdf">📥 Download Invoice (PDF)</a>'
            st.markdown(href, unsafe_allow_html=True)

            # Print Bill Button
            st.markdown(
                """
                <script>
                function printBill() { window.print(); }
                </script>
                <button onclick="printBill()">🖨 Print Bill</button>
                """,
                unsafe_allow_html=True
            )

            # WhatsApp Sending
            invoice_text = f"INDIA ELECTRONICS MART\nCustomer: {cust_name}\nPhone: {phone}\nAddress: {address}\nDate: {datetime.now()}\n\n"
            for _, row in df_cart.iterrows():
                invoice_text += f"{row['product']} x {row['qty']} = ₹{row['Total']:.2f}\n"
            invoice_text += f"\nGrand Total: ₹{grand_total:.2f}\nThank you for shopping!"
            msg = urllib.parse.quote(invoice_text)
            whatsapp_url = f"https://wa.me/{phone.replace('+', '')}?text={msg}"
            st.markdown(f"[📲 Send via WhatsApp]({whatsapp_url})")


# SEARCH BILLS
elif choice == "Search Bills":
    query = st.text_input("Search by Name or Phone")
    if query:
        results = search_bills(query)
        if results:
            df_bills = pd.DataFrame(results, columns=["Bill ID", "Name", "Phone", "Address", "Date", "Items", "Total"])
            st.dataframe(df_bills)
        else:
            st.warning("No matching bills found")
