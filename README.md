
# BusanSkyCapsuleBookingBot

## Introduciton
This tool supports booking Busan Sky Capsule tickets. If you want to book different ticket types, please modify the settings according to the instructions in the `.env` file. To change booking times or payment settings, also refer to the `.env` file. Currently, this tool only supports package ticket bookings.

## Installation

### Using UV

```bash
uv sync
playwright install
```
### Using requirements
```bash
pip install requirements.txt
playwright install
```

## Environment Setup

### Environment Configuration

If you want to modify any settings, make changes to the `.env` file:

```env
# modify your configuration here
VARIABLE_NAME=value
```

## Running the Application

```bash
uv run main.py
```

Or directly with Python:

```bash
python main.py
```

## Dependencies
- **Playwright**: Browser automation library for web scraping and testing. Required for the application to run.
