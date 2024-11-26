from fastapi import FastAPI, Depends, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import threading
import time
from datetime import datetime, timedelta
from .database import get_db, init_db
from .models import Portfolio, Holding, PriceHistory, Alert
from .alerts import AlertSystem
from .crypto_tracker import CryptoPortfolio
import asyncio
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse
from .config import get_settings

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
templates = Jinja2Templates(directory="app/web/templates")

security = HTTPBasic()

# Add these environment variables to your .env file
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "your_secure_password"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_specific_password"

class AlertSettings(BaseModel):
    email: str
    loss_threshold: float

# Add this to track initialization status
INITIALIZATION_STATUS = {
    "ready": False,
    "message": "Starting initialization..."
}

def init_portfolio(db: Session):
    """Initialize portfolio if it doesn't exist"""
    print("\n=== INITIALIZING PORTFOLIO ===")
    portfolio = db.query(Portfolio).first()
    
    if not portfolio:
        print("Creating new portfolio...")
        portfolio = Portfolio(
            initial_investment=110.0,
            current_value=0.0
        )
        db.add(portfolio)
        db.flush()
        
        # Create holdings
        holdings = [
            Holding(portfolio_id=portfolio.id, coin_id='ripple', amount=10.0, coins=0),
            Holding(portfolio_id=portfolio.id, coin_id='the-sandbox', amount=10.0, coins=0),
            Holding(portfolio_id=portfolio.id, coin_id='lido-dao', amount=10.0, coins=0),
            Holding(portfolio_id=portfolio.id, coin_id='uniswap', amount=20.0, coins=0),
            Holding(portfolio_id=portfolio.id, coin_id='solana', amount=20.0, coins=0),
            Holding(portfolio_id=portfolio.id, coin_id='ethereum', amount=40.0, coins=0)
        ]
        
        db.add_all(holdings)
        db.commit()
        print("Portfolio created with initial holdings")
    else:
        print("Portfolio already exists")
    
    return portfolio

def check_losses(db: Session):
    """Check for losses and send alerts if needed"""
    settings = db.query(AlertSettings).first()
    if not settings:
        return
    
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        return
    
    # Calculate total profit/loss percentage
    if portfolio.initial_investment > 0:
        profit_loss_pct = ((portfolio.current_value / portfolio.initial_investment) - 1) * 100
        
        if profit_loss_pct <= settings.loss_threshold:
            subject = f"Portfolio Alert: Loss Threshold Exceeded"
            body = f"""
Your portfolio has exceeded the loss threshold:

Initial Investment: ${portfolio.initial_investment:.2f}
Current Value: ${portfolio.current_value:.2f}
Profit/Loss: {profit_loss_pct:.1f}%

Individual Holdings:
"""
            for holding in portfolio.holdings:
                current_value = holding.coins * holding.current_price if holding.coins else 0
                profit_loss = current_value - holding.amount
                profit_loss_pct = ((current_value / holding.amount) - 1) * 100 if holding.amount else 0
                
                body += f"\n{holding.coin_id.title()}:"
                body += f"\n  Investment: ${holding.amount:.2f}"
                body += f"\n  Current Value: ${current_value:.2f}"
                body += f"\n  Profit/Loss: {profit_loss_pct:.1f}%"
            
            send_alert_email(settings.email, subject, body)

def background_task(db: Session):
    """Background task for initialization and updates"""
    global INITIALIZATION_STATUS
    
    print("\n=== Starting background task ===")
    try:
        # Initialize portfolio if needed
        INITIALIZATION_STATUS["message"] = "Creating portfolio..."
        portfolio = db.query(Portfolio).first()
        if not portfolio:
            print("Initializing portfolio...")
            init_portfolio(db)
        
        # Create portfolio manager
        portfolio_manager = CryptoPortfolio(db)
        
        # Initialize price history if needed
        if not db.query(PriceHistory).first():
            print("Initializing price history...")
            INITIALIZATION_STATUS["message"] = "Fetching initial price history..."
            success = portfolio_manager.initialize_price_history()
            if not success:
                raise Exception("Failed to initialize price history")
            
            INITIALIZATION_STATUS["message"] = "Calculating initial values..."
            success = portfolio_manager.calculate_coins()
            if not success:
                raise Exception("Failed to calculate initial values")
            
            INITIALIZATION_STATUS["message"] = "Initialization complete!"
            INITIALIZATION_STATUS["ready"] = True
        
        while True:
            try:
                print("\n=== Running background task ===")
                portfolio_manager.calculate_coins()
                portfolio_manager.save_price_history()
                
                # Sleep for 5 minutes
                print("Sleeping for 5 minutes...")
                time.sleep(300)
                
            except Exception as e:
                print(f"Error in background task loop: {e}")
                import traceback
                print(traceback.format_exc())
                time.sleep(60)
                
    except Exception as e:
        print(f"Error in background task initialization: {e}")
        import traceback
        print(traceback.format_exc())
        INITIALIZATION_STATUS["message"] = f"Error: {str(e)}"
        time.sleep(60)

@app.on_event("startup")
async def startup_event():
    init_db()
    db = next(get_db())
    thread = threading.Thread(target=background_task, args=(db,))
    thread.daemon = True
    thread.start()

# Add this function to check initialization status
def check_initialization_status(db: Session) -> bool:
    """Check if portfolio and price history are initialized"""
    portfolio = db.query(Portfolio).first()
    if not portfolio or portfolio.current_value == 0:
        return False
    
    # Check if we have price history
    price_history = db.query(PriceHistory).first()
    if not price_history:
        return False
    
    return True

@app.get("/")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard route"""
    try:
        # Check if we need to initialize
        portfolio = db.query(Portfolio).first()
        price_history = db.query(PriceHistory).first()
        
        if not portfolio or not price_history:
            print("Portfolio or price history missing - showing loading screen")
            return templates.TemplateResponse("loading.html", {
                "request": request,
                "status": INITIALIZATION_STATUS
            })

        # Get holdings with current values
        holdings = []
        total_value = 0
        
        for holding in portfolio.holdings:
            latest_price = db.query(PriceHistory)\
                .filter_by(coin_id=holding.coin_id)\
                .order_by(PriceHistory.timestamp.desc())\
                .first()
            
            if latest_price:
                current_price = float(latest_price.price)
                coins = holding.amount / current_price if current_price > 0 else 0
                current_value = coins * current_price
                total_value += current_value
                
                holdings.append({
                    'coin_id': holding.coin_id,
                    'amount': holding.amount,
                    'coins': coins,
                    'current_price': current_price,
                    'current_value': current_value
                })
        
        # Update portfolio value
        portfolio.current_value = total_value
        db.commit()

        # Get price history for graphs
        price_history = []
        for holding in portfolio.holdings:
            history = db.query(PriceHistory)\
                .filter_by(coin_id=holding.coin_id)\
                .order_by(PriceHistory.timestamp.asc())\
                .all()
            
            for ph in history:
                price_history.append({
                    'coin_id': ph.coin_id,
                    'timestamp': ph.timestamp.isoformat(),
                    'price': float(ph.price)
                })

        print(f"\nDashboard data ready:")
        print(f"Portfolio value: ${portfolio.current_value:.2f}")
        print(f"Number of holdings: {len(holdings)}")
        print(f"Price history points: {len(price_history)}")

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "portfolio": {
                "initial_investment": portfolio.initial_investment,
                "current_value": portfolio.current_value,
                "holdings": holdings
            },
            "price_history": price_history
        })

    except Exception as e:
        print(f"Error in dashboard route: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/current")
async def get_current_portfolio(db: Session = Depends(get_db)):
    crypto = CryptoPortfolio(db)
    current_prices = crypto.get_current_prices()
    portfolio = db.query(Portfolio).first()
    
    if not portfolio:
        return {"error": "No portfolio found"}
    
    holdings_data = []
    total_value = 0
    
    for holding in portfolio.holdings:
        if holding.coin_id in current_prices:
            current_price = current_prices[holding.coin_id]['usd']
            current_value = holding.coins * current_price
            total_value += current_value
            
            holdings_data.append({
                "coin_id": holding.coin_id,
                "amount": holding.amount,
                "coins": holding.coins,
                "current_value": current_value,
                "current_price": current_price
            })
    
    return {
        "current_value": total_value,
        "initial_investment": portfolio.initial_investment,
        "profit_loss": total_value - portfolio.initial_investment,
        "holdings": holdings_data
    }

@app.get("/api/rate-limits")
async def get_rate_limits(db: Session = Depends(get_db)):
    portfolio = CryptoPortfolio(db)
    return portfolio.get_remaining_api_calls()

@app.post("/api/alerts")
async def create_alert(
    coin_id: str,
    price_threshold: float,
    alert_type: str,
    user_email: str,
    db: Session = Depends(get_db)
):
    alert = Alert(
        coin_id=coin_id,
        price_threshold=price_threshold,
        alert_type=alert_type,
        user_email=user_email
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

# Define verify_admin first
def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    settings = get_settings()
    print("\n=== Auth Debug ===")
    print(f"Provided username: {credentials.username}")
    print(f"Expected username: {settings.ADMIN_USERNAME}")
    print(f"Provided password: {credentials.password}")
    print(f"Expected password: {settings.ADMIN_PASSWORD}")
    
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    
    print(f"Username match: {correct_username}")
    print(f"Password match: {correct_password}")
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

@app.get("/admin")
async def admin_dashboard(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    # Get alert settings
    alerts = db.query(Alert).all()
    portfolio = db.query(Portfolio).first()
    available_coins = [h.coin_id for h in portfolio.holdings]
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "alerts": alerts,
        "available_coins": available_coins
    })

@app.post("/admin/alerts")
async def update_alerts(
    request: Request,
    email: str = Form(...),
    loss_threshold: float = Form(...),
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not secrets.compare_digest(credentials.username, ADMIN_USERNAME) or \
       not secrets.compare_digest(credentials.password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401)
    
    # Update alert settings
    settings = db.query(AlertSettings).first()
    if not settings:
        settings = AlertSettings(email=email, loss_threshold=loss_threshold)
        db.add(settings)
    else:
        settings.email = email
        settings.loss_threshold = loss_threshold
    
    db.commit()
    
    return {"message": "Alert settings updated successfully"}

def send_alert_email(to_email: str, subject: str, body: str):
    """Send alert email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Alert email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.get("/alerts")
async def alert_dashboard(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    return RedirectResponse(url="/admin")  # Redirect /alerts to /admin

@app.post("/alerts/create")
async def create_alert(
    coin_id: str = Form(...),
    alert_type: str = Form(...),
    price_threshold: float = Form(...),
    user_email: str = Form(...),
    db: Session = Depends(get_db)
):
    alert = Alert(
        coin_id=coin_id,
        alert_type=alert_type,
        price_threshold=price_threshold,
        user_email=user_email,
        is_active=True
    )
    db.add(alert)
    db.commit()
    return {"message": "Alert created successfully"}

@app.post("/alerts/{alert_id}/toggle")
async def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.is_active = not alert.is_active
        db.commit()
    return {"status": "success"}

@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    db.query(Alert).filter(Alert.id == alert_id).delete()
    db.commit()
    return {"status": "success"}

@app.get("/status")
async def get_status():
    """Check initialization status"""
    return INITIALIZATION_STATUS