# FILE: product_service/services/rabbitmq_client.py

import pika
import json
import os

class RabbitMQClient:
    def __init__(self):
        # Беремо URL з середовища (з docker-compose), або використовуємо локальний для тестів
        self.rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://hits_admin:hits_password@localhost:5672/')
        self.connection = None
        self.channel = None

    def connect(self):
        """Встановлює з'єднання з RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            parameters = pika.URLParameters(self.rabbitmq_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

    def publish(self, queue_name: str, message: dict):
        """
        Відправляє повідомлення (словник) у вказану чергу.
        """
        self.connect()
        
        # durable=True означає, що черга переживе перезапуск RabbitMQ
        self.channel.queue_declare(queue=queue_name, durable=True)
        
        # Перетворюємо словник Python у JSON-рядок
        body = json.dumps(message)
        
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # 2 = повідомлення зберігається на диск (не втратиться при збої)
            )
        )
        print(f"📨 [RabbitMQ] Відправлено в чергу '{queue_name}': {body}")

    def close(self):
        """Закриває з'єднання"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

# Створюємо єдиний екземпляр (Singleton) для імпорту в інші файли
rabbitmq = RabbitMQClient()