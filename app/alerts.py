from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
from .models import Alert
from .config import get_settings

settings = get_settings()

class AlertSystem:
    def __init__(self, db: Session):
        self.db = db

    def check_alerts(self, current_prices: dict):
        active_alerts = self.db.query(Alert).filter(Alert.is_active == True).all()
        
        for alert in active_alerts:
            current_price = current_prices.get(alert.coin_id, {}).get('usd')
            if not current_price:
                continue
                
            should_trigger = (
                (alert.alert_type == 'above' and current_price > alert.price_threshold) or
                (alert.alert_type == 'below' and current_price < alert.price_threshold)
            )
            
            if should_trigger:
                self.trigger_alert(alert, current_price)

    def trigger_alert(self, alert: Alert, current_price: float):
        # Update last triggered time
        alert.last_triggered = datetime.utcnow()
        self.db.commit()
        
        # Send notification
        self.send_alert_email(
            alert.user_email,
            f"Price Alert: {alert.coin_id}",
            f"The price of {alert.coin_id} is now ${current_price:.2f}, "
            f"{'above' if alert.alert_type == 'above' else 'below'} your threshold of ${alert.price_threshold:.2f}"
        )

    def send_alert_email(self, to_email: str, subject: str, body: str):
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_USERNAME
            msg['To'] = to_email

            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}") 