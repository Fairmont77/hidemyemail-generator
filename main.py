import asyncio
import os
from rich.console import Console
from datetime import datetime

from icloud import HideMyEmail

WAIT_TIME = 60 * 60  # Static wait time in seconds
GENERATION_DELAY = 10  # Delay between email generations

class RichHideMyEmail(HideMyEmail):
    _cookie_file = "cookie.txt"

    def __init__(self):
        super().__init__()
        self.console = Console()
        self.rate_limit_reached = False
        self.log_file = "wait_time_log.txt"

        if os.path.exists(self._cookie_file):
            with open(self._cookie_file, "r") as f:
                self.cookies = [line.strip() for line in f if not line.startswith("//")][0]
        else:
            self.log(
                '[bold yellow][WARN][/] "cookie.txt" file not found! Generation may not work due to lack of authorization.'
            )

    def log(self, *args, **kwargs):
        self.console.log(*args, **kwargs)

    def get_error_message(self, error):
        if isinstance(error, dict):
            return error.get('errorMessage', str(error))
        else:
            return str(error)

    async def _generate_one(self) -> str:
        gen_res = await self.generate_email()

        if not gen_res or not gen_res.get("success"):
            error = gen_res.get("error", "Unknown error")
            error_message = self.get_error_message(error)
            self.log(f"[bold red][ERROR][/] Failed to generate email. Reason: {error_message}")
            if 'limit' in error_message.lower():
                self.rate_limit_reached = True
            return None

        email = gen_res["result"]["hme"]
        self.log(f'Generated email: "{email}"')

        reserve_res = await self.reserve_email(email)

        if not reserve_res or not reserve_res.get("success"):
            error = reserve_res.get("error", "Unknown error")
            error_message = self.get_error_message(error)
            self.log(f'[bold red][ERROR][/] Failed to reserve email. Reason: {error_message}')
            if 'limit' in error_message.lower():
                self.rate_limit_reached = True
            return None

        self.log(f'Reserved email: "{email}"')
        return email

    async def generate(self, count: int = 5):
        self.log(f"Generating {count} email(s)...")
        emails = []

        for _ in range(count):
            if self.rate_limit_reached:
                break

            email = await self._generate_one()
            if email:
                emails.append(email)
            await asyncio.sleep(GENERATION_DELAY)

        if emails:
            with open("emails.txt", "a+") as f:
                f.write(os.linesep.join(emails) + os.linesep)
            self.log('Emails have been saved into the "emails.txt" file')
            self.log(f"Successfully generated {len(emails)} email(s)")

        return emails

    def log_wait_time(self):
        with open(self.log_file, "a+") as log:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = "Rate limit reached" if self.rate_limit_reached else "Success"
            log.write(f"{timestamp} | Status: {status}\n")

async def periodic_generate():
    hme = RichHideMyEmail()
    while True:
        async with hme:
            await hme.generate(count=5)
        
        # Log the results
        hme.log_wait_time()

        if hme.rate_limit_reached:
            hme.log(
                f"[bold yellow]Rate limit reached. Waiting {WAIT_TIME / 60:.2f} minutes before next cycle.[/]"
            )
            hme.rate_limit_reached = False  # Reset rate limit flag
        else:
            hme.log(f"Waiting {WAIT_TIME / 60:.2f} minutes before next cycle...")

        await asyncio.sleep(WAIT_TIME)

if __name__ == "__main__":
    try:
        asyncio.run(periodic_generate())
    except KeyboardInterrupt:
        print("\nManual stop.")

