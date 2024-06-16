import asyncio
import random
from datetime import datetime, timedelta
from threading import Thread
import time

from flask import Flask, jsonify
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import requests

# Initialize data store
data_store = {
    'temperature': [],
    'humidity': [],
    'co2': [],
    'occupancy': []
}

# Function to simulate sensor data
async def simulate_sensor_data(sensor_type, min_val, max_val, interval):
    while True:
        value = round(random.uniform(min_val, max_val), 2)
        timestamp = datetime.now().isoformat()
        data_store[sensor_type].append({'timestamp': timestamp, 'value': value})
        # Keep only last 24 hours of data
        data_store[sensor_type] = [entry for entry in data_store[sensor_type] if datetime.fromisoformat(entry['timestamp']) > datetime.now() - timedelta(hours=24)]
        await asyncio.sleep(interval)

# Flask API setup
app = Flask(__name__)

@app.route('/api/sensor/<sensor_type>', methods=['GET'])
def get_sensor_data(sensor_type):
    if sensor_type in data_store:
        return jsonify(data_store[sensor_type])
    else:
        return jsonify({'error': 'Invalid sensor type'}), 404

# Function to run Flask app in a separate thread
def run_flask():
    app.run(debug=False, use_reloader=False)

# Start Flask app in a separate thread
flask_thread = Thread(target=run_flask)
flask_thread.start()

# Dash app setup
app_dash = dash.Dash(__name__)

app_dash.layout = html.Div([
    dcc.Interval(id='interval-component', interval=5*1000, n_intervals=0),
    html.Div([
        dcc.Graph(id='temperature-graph'),
        dcc.Graph(id='humidity-graph'),
        dcc.Graph(id='co2-graph'),
        dcc.Graph(id='occupancy-graph'),
    ])
])

@app_dash.callback(
    [Output('temperature-graph', 'figure'),
     Output('humidity-graph', 'figure'),
     Output('co2-graph', 'figure'),
     Output('occupancy-graph', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_graphs(n):
    base_url = 'http://127.0.0.1:5000/api/sensor/'
    sensor_data = {}
    try:
        for sensor in ['temperature', 'humidity', 'co2', 'occupancy']:
            response = requests.get(base_url + sensor)
            sensor_data[sensor] = response.json()
    except requests.exceptions.ConnectionError:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    def create_figure(sensor, title):
        data = sensor_data[sensor]
        x = [entry['timestamp'] for entry in data]
        y = [entry['value'] for entry in data]
        return {
            'data': [go.Scatter(x=x, y=y, mode='lines', name=sensor)],
            'layout': go.Layout(title=title)
        }

    return (create_figure('temperature', 'Temperature (°C)'),
            create_figure('humidity', 'Humidity (%)'),
            create_figure('co2', 'CO2 Levels (ppm)'),
            create_figure('occupancy', 'Occupancy'))

# Function to run Dash app in a separate thread
def run_dash():
    # Add delay to ensure Flask API is ready
    time.sleep(5)
    app_dash.run_server(debug=True, use_reloader=False)

# Start Dash app in a separate thread
dash_thread = Thread(target=run_dash)
dash_thread.start()

# Main function to run sensor data simulation
async def main():
    await asyncio.gather(
        simulate_sensor_data('temperature', 15, 30, 5),
        simulate_sensor_data('humidity', 30, 70, 7),
        simulate_sensor_data('co2', 300, 800, 10),
        simulate_sensor_data('occupancy', 0, 1, 3)
    )

# Start the simulation
asyncio.run(main())
