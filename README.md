# Crypto Portfolio Tracker

A real-time cryptocurrency portfolio tracking application that monitors your investments, calculates profit/loss, and sends price alerts.

## Features

- Real-time portfolio value tracking
- Profit/loss calculations with color-coded display
- Price history graphs
- Email price alerts
- Admin dashboard
- Automatic price updates every 5 minutes

## Prerequisites

- Docker and Docker Compose
- Gmail account for alerts
- CoinGecko API key

## Setup

1. Create a `.env` file:

```
cp .env.example .env
```

2. Run `docker compose up --build` to start the application.

3. Access the admin dashboard at `http://localhost:8000/admin`.

4. Add your crypto investments to the database using the admin interface.

5. The application will automatically track the value of your investments and send price alerts via email.

## Key Components

- **FastAPI**: API for tracking cryptocurrency investments and sending alerts.
- **PostgreSQL**: Database to store investment data.
- **Docker**: Containerization for easy deployment.
- **Gmail**: Email service for sending alerts.
- **CoinGecko API**: API for fetching cryptocurrency prices.

- `main.py`: FastAPI application and routes
- `models.py`: SQLAlchemy database models
- `crypto_tracker.py`: Portfolio tracking logic
- `alerts.py`: Price alert system
- `config.py`: Configuration management
- `database.py`: Database connection handling

## Database Models

1. Portfolio
   - Initial investment
   - Current value
   - Holdings relationship

2. Holdings
   - Coin ID
   - Investment amount
   - Number of coins
   - Current value

3. PriceHistory
   - Coin ID
   - Price
   - Timestamp

4. Alert
   - Coin ID
   - Alert type
   - Price threshold
   - Email
   - Status

## API Endpoints

- `/`: Main dashboard
- `/admin`: Admin dashboard
- `/alerts`: Price alerts management
- `/status`: Initialization status

## Background Tasks

- Portfolio initialization
- Price updates (every 5 minutes)
- Alert checking
- Price history recording

## Portfolio Setup

The application automatically tracks:
- Ethereum (ETH)
- Solana (SOL)
- Cardano (ADA)
- Ripple (XRP)

Initial investment amounts are set in the database initialization.

## Price Alerts

1. Access the admin dashboard (`/admin`)
2. Create new alerts:
   - Select coin
   - Set price threshold
   - Choose alert type (above/below)
   - Enter email address

## Email Setup

1. Gmail Configuration:
   - Enable 2-factor authentication
   - Generate App Password
   - Use App Password in `.env` file

2. Alert Types:
   - Price above threshold
   - Price below threshold

## Troubleshooting

- If you encounter issues with the application, ensure that Docker is properly installed and running.
- Check the logs for any errors or messages that can help diagnose the problem.
- If the issue persists, consider checking the CoinGecko API status or your network connection.


Common issues:
- Database connection errors: Check PostgreSQL settings
- Email alerts not working: Verify Gmail app password
- No data showing: Wait for initial price history to load
- Admin access denied: Check credentials in `.env`

## Development

Key files:
- `app/main.py`: Main application and routes
- `app/crypto_tracker.py`: Portfolio calculations
- `app/alerts.py`: Price alert system
- `app/models.py`: Database models
- `app/web/templates/`: HTML templates

## Features in Detail

### Dashboard
- Portfolio summary with total value
- Individual holdings breakdown
- Profit/loss calculations
- Color-coded profit/loss display (green/red)
- Price history graphs

### Admin Dashboard
- Price alert management
- Alert creation interface
- Active alerts overview
- Alert deletion

### Background Processing
- Automatic price updates
- Email notifications
- Price history tracking
- Portfolio value calculations

## Support

For issues or questions, please open a GitHub issue.
