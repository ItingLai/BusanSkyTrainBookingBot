from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import model_validator,Field,field_validator
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    ticketType: str = Field(alias="TICKET_TYPE")
    useStartTime: bool = Field(default=True, alias="USE_START_TIME")
    startTime: str | None = Field(default=None, alias="START_TIME")
    yearMonth: str = Field(alias="YEAR_MONTH")
    date: str = Field(alias="DATE")
    skyCapsuleTimeNumber: int = Field(alias="SKY_CAPSULE_TIME_NUMBER")
    beachTrainTimeNumber: int = Field(alias="BEACH_TRAIN_TIME_NUMBER")
    personNumbers: list[int] = Field(alias="PERSON_NUMBERS")
    orderName: str = Field(alias="ORDER_NAME")
    orderEmail: str = Field(alias="ORDER_EMAIL")
    orderPassword: str = Field(alias="ORDER_PASSWORD")
    orderCountry: str = Field(alias="ORDER_COUNTRY")
    PaymentMode: str = Field(default="Card", alias="PAYMENT_MODE")
    PaymentNetwork: str = Field(default="Visa", alias="PAYMENT_NETWORK")
    PaymentCardNumber: str | None = Field(default=None, alias="PAYMENT_CARD_NUMBER")
    PaymentCardExpiry_y: int | None = Field(default=None, alias="PAYMENT_CARD_EXPIRY_Y")
    PaymentCardExpiry_m: int | None = Field(default=None, alias="PAYMENT_CARD_EXPIRY_M")
    PaymentCardHolderName: str | None = Field(default=None, alias="PAYMENT_CARD_HOLDER_NAME")
    paymentCardEmail: str | None = Field(default=None, alias="PAYMENT_CARD_EMAIL")

    @model_validator(mode="after")
    def check_card_fields(self):
        if self.PaymentMode == "Card":
            if not self.PaymentCardNumber or not self.PaymentCardExpiry_y or not self.PaymentCardExpiry_m or not self.PaymentCardHolderName:
                raise ValueError("if use the Card ，PaymentCardNumber、PaymentCardExpiry、PaymentCardHolderName must be filled.")
            if time.localtime().tm_year > self.PaymentCardExpiry_y or (time.localtime().tm_year == self.PaymentCardExpiry_y and time.localtime().tm_mon > self.PaymentCardExpiry_m):
                raise ValueError("the card is expired.")
        return self

    @field_validator("orderCountry")
    def check_country(cls, v):
        if not v:
            raise ValueError("orderCountry must be filled.")
        return v.upper()

def get_required_env(name: str) -> str:
    path = Path(name)
    if not path.exists():
        raise FileNotFoundError(".env file not found!")
    return Settings()

# alert auto accept
def auto_accept_dialog(dialog):
    dialog.accept()  

def main_page_control(page, context, settings: Settings):
    # wait for the page to load
    page.wait_for_selector("#titleGoodsName")

    # calendar select
    while True:
        header = page.locator("#calYyyyMM").inner_text()
        ym= settings.yearMonth.replace("-", " ")
        if ym in header :
            date_btn_id = f"{ym.replace(' ', '')}{int(settings.date):02d}"
            page.wait_for_function(
                f'document.getElementById("{date_btn_id}").classList.contains("live")',
                timeout=10000
            )
            page.locator(f'id={date_btn_id}').click()
            break
        page.click("#moveNextMonth")
    
    # wait for the schedule to load    
    page.wait_for_timeout(1000)
    # sky capsule time select
    page.locator("div[data-langnum='default_schedule_select_txt']").nth(1).click()
    page.locator(".scheduleInfoSelectUl").nth(0).locator("li").nth(settings.skyCapsuleTimeNumber-1).click()
    # beach train time select
    page.locator("div[data-langnum='default_schedule_select_txt']").nth(2).click()
    page.locator(".scheduleInfoSelectUl").nth(1).locator("li").nth(settings.beachTrainTimeNumber-1).click()

    # choose person number
    for persons in settings.personNumbers:
        if persons < 2:
            persons = 2
        elif persons > 4:
            raise ValueError("person number must be between 2 and 4.")
        
        page.locator(f"span.plus[data-num='{persons-1}']").click()


    # fill order info
    page.fill("#rsBuyerName", settings.orderName)
    page.fill("#email", settings.orderEmail)
    page.fill("#rsBuyerPwd", settings.orderPassword)
    page.select_option("#national", settings.orderCountry)

    page.locator("label[for='agreeAll']").click()
    page.locator("label[for='agree5']").click()
    page.locator("div[data-langnum='default_payment_select_txt']").click()
    page.locator("li[data-value='FOREIGNCARD']").click()

    # Credit card iframe
    with context.expect_page() as new_page_info:
        page.locator("a[data-langnum='btn_pay_reserve_txt']").click()
    
    return new_page_info.value

def payment_page_control(payment_page, settings: Settings):
    # wait for the payment page to load
    payment_page.wait_for_timeout(2000)
    payment_page.wait_for_load_state("domcontentloaded")
    # get the payment iframe
    payment_iframe = payment_page.frame_locator('#frame_content')
    # agree to terms and conditions
    payment_iframe.locator("#agreeAll").click()
    payment_iframe.locator("a.a_confirm").click()
    # wait for the next page to load
    payment_page.wait_for_timeout(1000)
    # choose network and card
    payment_iframe.locator("#a_sel_etccard").click()
    payment_iframe.locator(f"a[title='{settings.PaymentNetwork}']").click()
    payment_iframe.locator("a.a_confirm").click()
    # wait for the next page to load
    payment_page.wait_for_timeout(1000)
    # fill card info
    for i in range(1, 3):
        payment_iframe.locator(f"#card{i}").fill(settings.PaymentCardNumber[(i-1)*4:i*4])
    for i in range(3, 5):
        card_num = settings.PaymentCardNumber[(i-1)*4:i*4]
        payment_iframe.locator(f"#card{i}").click()
        for num in card_num:
            payment_iframe.locator(f"#card{i}_layout .transkey_div_3 [aria-label='{num}']").click()
    #open the dropdown for mm and choose the month
    payment_iframe.locator("#a_sel_expr_mm").click()
    payment_iframe.locator("#div_expr_mm ul li a").nth(settings.PaymentCardExpiry_m - 1).click()
    #open the dropdown for yy and choose the year
    payment_iframe.locator("#a_sel_expr_yy").click()
    payment_iframe.locator(f"#div_expr_yy ul li a:has-text('{settings.PaymentCardExpiry_y}')").click()
    # fill card holder name and email
    payment_iframe.locator("#REQ_cardholder_nm").fill(settings.PaymentCardHolderName)
    payment_iframe.locator("#REQ_user_mail").fill(settings.paymentCardEmail)
    payment_iframe.locator("a#btn_next").click()



def main(settings: Settings):
    ticket_url_set = {
        "1": "https://www.tbluelinepark.com/ticket_eng/GD2100115", # departure:mipo,first facility: sky capsule
        "2": "https://www.tbluelinepark.com/ticket_eng/GD2100058", # departure:mipo,first facility: beach train
        "3": "https://www.tbluelinepark.com/ticket_eng/GD2100129", # departure:Cheongsapo,first facility: sky capsule
        "4": "https://www.tbluelinepark.com/ticket_eng/GD2100105", # departure:Cheongsapo,first facility: beach train
    }
    ticket_url = ticket_url_set.get(settings.ticketType)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=50
        )
        context = browser.new_context()
        page = context.new_page()
        page.on("dialog", auto_accept_dialog)  # bind dialog event to auto accept function
        page.goto(ticket_url)

        if settings.useStartTime and settings.startTime:
            start_time_struct = time.strptime(settings.startTime, "%Y-%m-%d %H:%M:%S")
            start_timestamp = time.mktime(start_time_struct)
            while time.time() < start_timestamp:
                try:
                    _ = page.title()
                except Exception:
                    break
                print(f"Waiting for start time... {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
                page.wait_for_timeout(1000)


        payment_page = main_page_control(page, context, settings)
        
        payment_page_control(payment_page, settings)

        input("press Enter to close...")
        browser.close() 


if __name__ == "__main__":
    settings = get_required_env(".env")
    main(settings)
