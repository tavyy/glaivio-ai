from .whatsapp import WhatsAppChannel
from .sms import SMSChannel
from .web import WebChannel
from .gmail import GmailChannel

CHANNELS = {
    "whatsapp": WhatsAppChannel,
    "sms": SMSChannel,
    "web": WebChannel,
    "gmail": GmailChannel,
}


def get_channel(name: str):
    if name not in CHANNELS:
        raise ValueError(f"Unknown channel '{name}'. Available: {list(CHANNELS.keys())}")
    return CHANNELS[name]()
