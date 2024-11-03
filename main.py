import asyncio
import os
from rich.console import Console

from icloud import HideMyEmail

MAX_CONCURRENT_TASKS = 10
WAIT_TIME = 45 * 60  # 45 хвилин (2700 секунд)

class RichHideMyEmail(HideMyEmail):
    _cookie_file = "cookie.txt"

    def __init__(self):
        super().__init__()
        self.console = Console()

        if os.path.exists(self._cookie_file):
            with open(self._cookie_file, "r") as f:
                self.cookies = [line for line in f if not line.startswith("//")][0]
        else:
            self.console.log(
                '[bold yellow][WARN][/] No "cookie.txt" file found! Generation might not work due to unauthorized access.'
            )

    async def _generate_one(self) -> str:
        # First, generate an email
        gen_res = await self.generate_email()

        if not gen_res or not gen_res.get("success"):
            error = gen_res.get("error", "Unknown error")
            self.console.log(f"[bold red][ERR][/] Failed to generate email. Reason: {error}")
            return None

        email = gen_res["result"]["hme"]
        self.console.log(f'[50%] "{email}" - Successfully generated')

        # Then, reserve it
        reserve_res = await self.reserve_email(email)

        if not reserve_res or not reserve_res.get("success"):
            error = reserve_res.get("error", "Unknown error")
            self.console.log(f'[bold red][ERR][/] Failed to reserve email. Reason: {error}')
            return None

        self.console.log(f'[100%] "{email}" - Successfully reserved')
        return email

    async def generate(self, count: int = 5):
        self.console.log(f"Generating {count} email(s)...")
        emails = []

        for _ in range(count):
            email = await self._generate_one()
            if email:
                emails.append(email)

        if emails:
            with open("emails.txt", "a+") as f:
                f.write(os.linesep.join(emails) + os.linesep)
            self.console.log(f':star: Emails have been saved into the "emails.txt" file')
            self.console.log(f"[bold green]All done![/] Successfully generated {len(emails)} email(s)")

        return emails

async def periodic_generate():
    while True:
        # Створюємо екземпляр класу HideMyEmail для генерації
        async with RichHideMyEmail() as hme:
            await hme.generate(count=5)  # Генеруємо 5 email'ів кожен раз

        # Очікування 45 хвилин перед наступною генерацією
        print(f"Зачекайте 45 хвилин до наступного запуску...")
        await asyncio.sleep(WAIT_TIME)

if __name__ == "__main__":
    try:
        asyncio.run(periodic_generate())
    except KeyboardInterrupt:
        print("\nЗупинено вручну.")


