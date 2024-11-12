import asyncio
import os
import datetime
import random

from typing import Optional, List
from rich.console import Console
from rich.prompt import IntPrompt
from rich.text import Text
from rich.table import Table

from icloud import HideMyEmail


MINUTES = random.randint(60,120)
WAIT_TIME = MINUTES * 60  # Static wait time in seconds (60 minutes)
GENERATION_DELAY = random.randint(10, 30)  # Delay between email generations (10 seconds)

class RichHideMyEmail(HideMyEmail):
    _cookie_file = "cookie.txt"

    def __init__(self):
        super().__init__()
        self.console = Console()
        self.rate_limit_reached = False
        self.log_file = "wait_time_log.txt"  # File to save logs
        self.table = Table()

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

    async def _generate_one(self) -> Optional[str]:
        # First, generate an email
        gen_res = await self.generate_email()

        if not gen_res or not gen_res.get("success"):
            error = gen_res.get("error", "Unknown error")
            error_message = self.get_error_message(error)
            self.log(f"[bold red][ERROR][/] Failed to generate email. Reason: {error_message}")
            if 'limit' in error_message.lower():
                self.rate_limit_reached = True
            return None

        email = gen_res["result"]["hme"]
        self.log(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Generated email: "{email}"')

        # Now, reserve the email
        reserve_res = await self.reserve_email(email)

        if not reserve_res or not reserve_res.get("success"):
            error = reserve_res.get("error", "Unknown error")
            error_message = self.get_error_message(error)
            self.log(f'[bold red][ERROR][/] Failed to reserve email. Reason: {error_message}')
            if 'limit' in error_message.lower():
                self.rate_limit_reached = True
            return None

        self.log(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Reserved email: "{email}"')
        return email

    async def generate(self, count: Optional[int] = None) -> List[str]:
        try:
            emails = []
            self.console.rule()
            if count is None:
                s = IntPrompt.ask(
                    Text.assemble(("How many iCloud emails do you want to generate?")),
                    console=self.console,
                )
                count = int(s)
            self.log(f"Generating {count} email(s)...")
            self.console.rule()
            with self.console.status(f"[bold green]Generating iCloud email(s)..."):
                for _ in range(count):
                    if self.rate_limit_reached:
                        break  # Stop if rate limit is reached
                    email = await self._generate_one()
                    if email:
                        emails.append(email)
                    # Delay between each email generation
                    await asyncio.sleep(GENERATION_DELAY)
            if emails:
                with open("emails.txt", "a+") as f:
                    f.write(os.linesep.join(emails) + os.linesep)
                self.console.rule()
                self.log(
                    f':star: Emails have been saved into the "emails.txt" file'
                )
                self.log(
                    f"[bold green]All done![/] Successfully generated [bold green]{len(emails)}[/] email(s)"
                )
            return emails
        except KeyboardInterrupt:
            return []

    async def list(self, active: Optional[bool] = None, search: Optional[str] = None) -> None:
        gen_res = await self.list_email()
        if not gen_res:
            return
        if "success" not in gen_res or not gen_res["success"]:
            error = gen_res.get("error", {})
            err_msg = self.get_error_message(error)
            self.log(
                f"[bold red][ERR][/] - Failed to list emails. Reason: {err_msg}"
            )
            return

        self.table = Table(title="Hide My Email Addresses")
        self.table.add_column("Label")
        self.table.add_column("Hide My Email")
        self.table.add_column("Created Date Time")
        self.table.add_column("IsActive")

        emails_to_save = []  # List to hold emails for saving

        for row in gen_res["result"]["hmeEmails"]:
            if active is None or row["isActive"] == active:
                if search is None or (search and search.lower() in row["label"].lower()):
                    created_time = datetime.datetime.fromtimestamp(row["createTimestamp"] / 1000)
                    formatted_time = created_time.strftime("%Y-%m-%d %H:%M:%S")
                    self.table.add_row(
                        row.get("label", ""),
                        row["hme"],
                        formatted_time,
                        str(row["isActive"]),
                    )
                    # Add email to the list for saving
                    emails_to_save.append(
                        f"{row.get('label', '')},{row['hme']},{formatted_time},{str(row['isActive'])}")

        # Display the table in console
        self.console.print(self.table)

        # Save emails to a file
        with open("all_emails.txt", "w") as file:
            file.write("\n".join(emails_to_save))
        self.log(f"All emails saved to 'all_emails.txt'")

    def log_wait_time(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Rate limit reached" if self.rate_limit_reached else "Success"
        with open(self.log_file, "a+") as log:
            log.write(f"{timestamp} | Status: {status}\n")

async def generate(count: Optional[int] = None) -> None:
    async with RichHideMyEmail() as hme:
        await hme.generate(count)

async def list_emails(active: bool = True, search: Optional[str] = None) -> None:
    async with RichHideMyEmail() as hme:
        await hme.list(active, search)

async def periodic_generate():
    hme = RichHideMyEmail()
    while True:
        async with hme:
            await hme.generate(count=random.randint(1, 5))

        # Випадковий час очікування для кожного циклу
        WAIT_TIME = random.randint(60, 120) * 60

        # Запис лога
        hme.log_wait_time()
        if hme.rate_limit_reached:
            hme.log(f"[bold yellow]Rate limit reached. Waiting {WAIT_TIME / 60:.2f} minutes before next cycle.[/]")
            hme.rate_limit_reached = False
        else:
            hme.log(f"Waiting {WAIT_TIME / 60:.2f} minutes before next cycle...")

        await asyncio.sleep(WAIT_TIME)



if __name__ == "__main__":
    try:
        choice = input("Enter 'generate' to generate emails or 'list' to list all emails: ").strip().lower()

        if choice == 'generate':
            asyncio.run(periodic_generate())
        elif choice == 'list':
            asyncio.run(list_emails(active=None))  # Pass `None` to show all emails
        else:
            print("Invalid choice. Please enter 'generate' or 'list'.")
    except KeyboardInterrupt:
        print("\nManual stop.")


