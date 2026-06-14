import json
from channels.generic.websocket import AsyncWebsocketConsumer
from detector.fraud_detector import FraudDetector
fraud_detector = FraudDetector()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        sender = data.get("sender", "Anonymous")
        label, confidence = fraud_detector.classify_message(message)
        is_fraud = label.lower().startswith("мошенничество")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender,
                'is_fraud': is_fraud
            }
        )

    async def chat_message(self, event):
        print("CHAT MESSAGE EVENT:", event)

        await self.send(text_data=json.dumps({
            'id': event.get('id'),
            'message': event.get('message'),
            'sender': event.get('sender'),
            'timestamp': event.get('timestamp'),
            'is_fraud': event.get('is_fraud', False),
            'fraud_confidence': event.get('fraud_confidence'),
            'message_type': event.get('message_type', 'text'),
            'audio_url': event.get('audio_url'),
            'transcript': event.get('transcript', '')
        }))
