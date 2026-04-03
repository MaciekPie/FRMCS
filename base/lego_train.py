from bleak import BleakClient

LEGO_HUB_CHARACTERISTIC = "00001624-1212-efde-1623-785feabcd123"

class LegoTrain:
    def __init__(self, name, mac):
        self.name = name
        self.mac = mac
        self.client = None
        self.light_on = False
        self.speed = 0

    async def connect(self):
        try:
            print(f"Łączenie z {self.name} ({self.mac})...")
            self.client = BleakClient(self.mac)
            await self.client.connect()
            print(f"Połączono z {self.name}!")
        except Exception as e:
            print(f"Błąd połączenia z {self.name}: {e}")

    async def send_speed(self, target_speed):
        try:
            if 0 < target_speed < 40:
                if self.speed == 0:
                    self.speed = 40
                else:
                    self.speed = 0
            elif -40 < target_speed < 0:
                if self.speed == 0:
                    self.speed = -40
                else:
                    self.speed = 0
            else:
                self.speed = max(-80, min(80, target_speed))

            speed_val = int(self.speed).to_bytes(1, byteorder='little', signed=True)[0]
            payload = bytearray([0x08, 0x00, 0x81, 0x00, 0x11, 0x51, 0x00, speed_val])
            await self.client.write_gatt_char(LEGO_HUB_CHARACTERISTIC, payload)
        except Exception as e:
            print(f"\nBłąd komunikacji z {self.name} (Prędkość): {e}")

    async def set_light(self, brightness):
        try:
            brightness = max(0, min(100, int(brightness)))
            payload = bytearray([0x08, 0x00, 0x81, 0x01, 0x11, 0x51, 0x00, brightness])
            await self.client.write_gatt_char(LEGO_HUB_CHARACTERISTIC, payload)
            self.light_on = brightness > 0
        except Exception as e:
            print(f"\nBłąd komunikacji z {self.name} (Światła): {e}")

    async def stop(self):
        self.speed = 0
        await self.send_speed(0)