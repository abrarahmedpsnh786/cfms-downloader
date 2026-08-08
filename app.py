import streamlit as st
import asyncio
import os
import re
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from playwright.async_api import async_playwright
from pypdf import PdfWriter

# Install Playwright Chromium Automatically on Cloud Startup
@st.cache_resource
def install_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        subprocess.run(["playwright", "install-deps"], check=True)
    except Exception as e:
        print(f"Playwright Install Warning: {e}")

install_playwright_browsers()

# SHC Credentials
SHC_EMAIL = "adocate33@gmail.com"
SHC_PASS = "advocate33"

# Email Configuration
TARGET_EMAIL = "abrarahmedpsnk786@gmail.com"
SENDER_EMAIL = "adocate33@gmail.com"
SENDER_PASSWORD = "advocate33"

st.set_page_config(page_title="CFMS Downloader", page_icon="⚖️", layout="centered")

st.title("⚖️ CFMS & SHC Case Downloader")
st.write("Worldwide Mobile & Desktop Portal")

# Input Fields
district = st.text_input("District", value="Naushahro Feroze")
ps = st.text_input("Police Station", value="Kandiaro")
fir = st.text_input("FIR / Crime Number", placeholder="e.g. 77")
year = st.text_input("Crime Year", value="2026")
accused = st.text_input("Accused Name (Optional)")

def send_pdf_email(pdf_file_path, recipient_email):
    """Function to send PDF directly to user's email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = f"CFMS Diaries PDF - FIR {fir}/{year} ({ps})"

        body = f"Assalam-o-Alaikum,\n\nAttached is the requested CFMS Case Diaries PDF for FIR No. {fir}/{year}, PS: {ps}.\n\nRegards,\nCFMS Automation System"
        msg.attach(MIMEText(body, 'plain'))

        with open(pdf_file_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(pdf_file_path)}")
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

async def run_automation():
    folder_name = f"FIR_{fir}_{year}_{ps.replace(' ', '_')}"
    judgements_folder = os.path.join(folder_name, "Judgements")
    os.makedirs(judgements_folder, exist_ok=True)

    status = st.empty()
    status.info("🌐 Step 1: Searching CFMS Portal...")

    async with async_playwright() as p:
        # Launch Chromium with Linux Cloud Sandbox Bypass Arguments
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote"
            ]
        )
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            await page.goto("https://cases.districtcourtssindh.gos.pk", wait_until="domcontentloaded")
            await page.select_option("select#district", label=district)
            await page.click("button[data-bs-target='#collapseOne']")
            await asyncio.sleep(0.5)

            await page.select_option("select#policeStation", label=ps)
            await page.fill("input[name='firno']", fir)
            await page.fill("input[name='firyear']", year)
            if accused:
                await page.fill("input#pname", accused)

            await page.click("button[type='submit']:has-text('Search')")
            await page.wait_for_selector("table tbody tr", timeout=15000)
        except Exception as e:
            st.error(f"Search error: {e}")

        rows = page.locator("table tbody tr")
        total_rows = await rows.count()
        st.write(f"📊 Found {total_rows} case(s) on CFMS.")

        cases_info = []
        downloaded_diaries = []

        for idx in range(total_rows):
            d_page = await context.new_page()
            try:
                await d_page.goto("https://cases.districtcourtssindh.gos.pk")
                await d_page.select_option("select#district", label=district)
                await d_page.click("button[data-bs-target='#collapseOne']")
                await asyncio.sleep(0.5)
                await d_page.select_option("select#policeStation", label=ps)
                await d_page.fill("input[name='firno']", fir)
                await d_page.fill("input[name='firyear']", year)
                await d_page.click("button[type='submit']:has-text('Search')")
                await d_page.wait_for_selector("table tbody tr")

                eye = d_page.locator("table tbody tr").nth(idx).locator("i.fa-eye, a, button").first
                await eye.click()
                await d_page.wait_for_timeout(2500)

                diary_text = await d_page.locator("body").inner_text()

                c_no, c_yr = "", ""
                num_match = re.search(r'(\d+)\s*/\s*(\d{4})', diary_text)
                if num_match:
                    c_no, c_yr = num_match.group(1), num_match.group(2)

                c_type = ""
                t_match = re.search(r'(Criminal\s+Bail\s+Application|Sessions\s+Case|Direct\s+Complaint)', diary_text, re.I)
                if t_match:
                    c_type = t_match.group(1)

                pdf_path = os.path.join(folder_name, f"Diary_Case_{c_no}_{c_yr}.pdf")
                await d_page.pdf(path=pdf_path, format="A4")
                downloaded_diaries.append(pdf_path)

                cases_info.append({"case_no": c_no, "case_year": c_yr, "case_type": c_type})
                st.success(f"✅ Scanned: {c_type} {c_no}/{c_yr}")
                await d_page.close()
            except Exception:
                await d_page.close()

        if downloaded_diaries:
            merged_file = os.path.join(folder_name, f"ALL_DIARIES_{fir}_{year}.pdf")
            merger = PdfWriter()
            for pdf in downloaded_diaries:
                merger.append(pdf)
            merger.write(merged_file)
            merger.close()

            # Mobile direct download button
            with open(merged_file, "rb") as f:
                st.download_button("📥 Download Merged Diaries PDF", f, file_name=f"ALL_DIARIES_{fir}_{year}.pdf")

            # Send Email
            st.info(f"📧 Sending PDF to {TARGET_EMAIL}...")
            email_sent = send_pdf_email(merged_file, TARGET_EMAIL)
            if email_sent:
                st.success(f"📩 Email successfully sent to {TARGET_EMAIL}!")
            else:
                st.warning("⚠️ Could not send email automatically (Check SMTP credentials).")

        status.success("🎉 Complete Process Finished!")
        await browser.close()

if st.button("Start Download Process", type="primary"):
    if not fir or not year:
        st.error("FIR and Year required!")
    else:
        asyncio.run(run_automation())
