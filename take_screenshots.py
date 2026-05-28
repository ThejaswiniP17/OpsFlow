import os
import time
from playwright.sync_api import sync_playwright

def main():
    # Make sure screenshots folder exists
    os.makedirs(r"C:\Users\hp\Desktop\opsflow\screenshots", exist_ok=True)
    
    with sync_playwright() as p:
        # Launch headless browser
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        # Set large desktop resolution
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        # 1. Login Page Screenshot
        print("Navigating to login page...")
        page.goto("http://127.0.0.1:8000/accounts/login/")
        page.wait_for_timeout(1500)  # Wait for load and animations
        
        login_path = r"C:\Users\hp\Desktop\opsflow\screenshots\actual_login.png"
        page.screenshot(path=login_path)
        print(f"Login page screenshot saved to: {login_path}")
        
        # 2. Authenticate
        print("Entering credentials...")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin123")
        page.click("button[type='submit']")
        
        # Wait for redirect to complete
        print("Waiting for dashboard to load...")
        page.wait_for_url("http://127.0.0.1:8000/")
        
        # Wait for Chart.js draw animations to finish
        print("Waiting for Chart.js rendering...")
        page.wait_for_timeout(3500)
        
        dashboard_path = r"C:\Users\hp\Desktop\opsflow\screenshots\actual_dashboard.png"
        page.screenshot(path=dashboard_path)
        print(f"Dashboard screenshot saved to: {dashboard_path}")
        
        browser.close()
        print("Done capturing actual screenshots!")

if __name__ == "__main__":
    main()
