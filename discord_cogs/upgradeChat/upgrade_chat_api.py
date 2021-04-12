from upgradeChat import API as upgradeChat

class UpgradeChatInstance:
    def __init__(self,
                 upgrade_chat_credentials: dict):
        self.api = upgradeChat(client_id=upgrade_chat_credentials.get('client_id'),
                               client_secret=upgrade_chat_credentials.get('client_secret'))


    @property
    def users(self):
        return self.api.users

    @property
    def products(self):
        return self.api.products

    @property
    def orders(self):
        return self.api.orders

    @property
    def webhooks(self):
        return self.api.webhooks

    @property
    def webhook_events(self):
        return self.api.webhook_events

    def get_orders_for_user(self, discord_id: int):
        return self.api.get_orders(discord_id=discord_id)
