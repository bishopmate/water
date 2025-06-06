import asyncio
import csv
import os
import aiohttp
from pydantic import BaseModel
from water import createTask, Flow

# --- Schemas ---

class WeatherInput(BaseModel):
    city: str
    api_key: str

class WeatherOutput(BaseModel):
    temperature: float
    conditions: str

class SaveInput(BaseModel):
    temperature: float
    conditions: str

class SaveOutput(BaseModel):
    file_path: str

# --- Tasks ---

async def fetch_weather(params):
    city = params["input_data"]["city"]
    api_key = params["input_data"]["api_key"]
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return {
                "temperature": data["main"]["temp"],
                "conditions": data["weather"][0]["description"]
            }

def save_weather(params):
    temperature = params["input_data"]["temperature"]
    conditions = params["input_data"]["conditions"]
    file_path = "weather_data.csv"
    file_exists = os.path.exists(file_path)
    with open(file_path, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Temperature", "Conditions"])
        writer.writerow([temperature, conditions])
    return {"file_path": file_path}

fetch_task = createTask(
    id="fetch_weather",
    description="Fetch weather data from OpenWeatherMap",
    inputSchema=WeatherInput,
    outputSchema=WeatherOutput,
    execute=fetch_weather
)

save_task = createTask(
    id="save_weather",
    description="Save weather data to CSV",
    inputSchema=SaveInput,
    outputSchema=SaveOutput,
    execute=save_weather
)

# --- Flow ---

flow = Flow("weather_pipeline", "Fetch and save weather data")
flow.then(fetch_task).then(save_task).register()

# --- Run ---

async def main():
    api_key = "YOUR_OPENWEATHERMAP_API_KEY"  # Replace with your actual API key
    result = await flow.run({"city": "London", "api_key": api_key})
    print(f"Weather data saved to: {result['file_path']}")

if __name__ == "__main__":
    asyncio.run(main())