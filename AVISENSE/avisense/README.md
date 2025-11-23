# Avisense - Engine Safety Prediction System

Avisense is a modern, responsive web frontend for predicting aircraft engine safety based on telemetry data. It allows technicians to input flight data and receive instant safety verdicts using a machine learning model.

## Features

- **Quick Check**: Instant safety prediction with confidence score and explanation.
- **History**: Log of previous checks with CSV export.
- **Diagnostics**: Time-series visualization of engine telemetry.
- **Settings**: Configuration for API endpoints and alerts.
- **Responsive Design**: Optimized for desktop and mobile devices.
- **Accessibility**: High-contrast mode support and keyboard navigation.

## Tech Stack

- **Frontend**: React (Vite)
- **Styling**: Vanilla CSS (CSS Modules) with a custom Design System
- **Charts**: Recharts
- **Icons**: Lucide React
- **ML Model**: Python (Scikit-Learn)

## Getting Started

### Prerequisites

- Node.js (v16+)
- Python 3.8+ (for model training script)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd avisense
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:5173](http://localhost:5173) in your browser.

### ML Model Training

To train the improved machine learning model:

1. Navigate to the `model` directory:
   ```bash
   cd model
   ```

2. Install requirements (pandas, scikit-learn):
   ```bash
   pip install pandas scikit-learn
   ```

3. Run the training script:
   ```bash
   python train_model.py
   ```

## API Integration

The frontend is currently configured to use a mock API service for demonstration. To connect to a real backend:

1. Go to the **Settings** page in the app.
2. Update the **Backend API Endpoint** URL.
3. The app expects a POST request to the endpoint with the telemetry JSON payload.

## Project Structure

- `src/components`: Reusable UI components (FormInput, ResultCard, etc.)
- `src/pages`: Main application views
- `src/services`: API integration and mock services
- `src/styles`: Global CSS variables and resets
- `model`: Python ML model training scripts

## License

MIT
