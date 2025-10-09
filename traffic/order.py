"""Prometheus exporter that generates live random fast-food orders."""

from __future__ import annotations
import time
import os
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Configuration
EXPORT_PORT = int(os.getenv("ORDER_METRICS_PORT", "9101"))

# Program start timestamp in milliseconds — initialized when main() starts
PROGRAM_START_MS = 0

# Restaurant ambient data ranges
TEMPERATURE_RANGE = (180.0, 240.0)  # Celsius
NOISE_LEVEL_RANGE = (40, 85)  # Decibels
POWER_USAGE_RANGE = (8000, 12000)  # Watts
ICE_CREAM_TEMP_RANGE = (-22, -18)  # Celsius
BATHROOM_CAPACITY = 4  # Number of stalls

# Convert all times to milliseconds
PROCESSING_TIMES = {
    "fries": (170, 200),  # 170-200ms
    "milkshake": (100, 150)  # 100-150ms
}

MACHINES = {
    "fries": 10,
    "milkshake": 10
}

ORDERS_PER_INTERVAL = (2, 5)  # Random number of orders generated per interval
INTERVAL_MS = 10  # Generate orders every 100ms

@dataclass
class Order:
    item: str
    processing_time: float  # in milliseconds
    start_time: float  # in milliseconds
    created_time: float  # in milliseconds
    queued: bool = True
    
    @property
    def is_completed(self) -> bool:
        return time.time() * 1000 >= self.start_time + self.processing_time
        
    @property
    def elapsed_time(self) -> float:
        return time.time() * 1000 - self.start_time  # keep as milliseconds

# Restaurant Environment Metrics
AMBIENT_TEMP = Gauge(
    "restaurant_temperature_celsius",
    "Restaurant ambient temperature in Celsius",
)
NOISE_LEVEL = Gauge(
    "restaurant_noise_level_db",
    "Restaurant noise level in decibels",
)
POWER_USAGE = Gauge(
    "restaurant_power_usage_watts",
    "Total restaurant power consumption in watts",
)
ICE_CREAM_TEMP = Gauge(
    "restaurant_ice_cream_temp_celsius",
    "Ice cream machine temperature in Celsius",
)
BATHROOM_OCCUPANCY = Gauge(
    "restaurant_bathroom_occupancy",
    "Number of occupied bathroom stalls",
    labelnames=("gender",),  # 'M' or 'F'
)
BATHROOM_QUEUE = Gauge(
    "restaurant_bathroom_queue",
    "Number of people waiting for bathroom",
    labelnames=("gender",),  # 'M' or 'F'
)
BATHROOM_VISITS = Counter(
    "restaurant_bathroom_visits_total",
    "Total number of bathroom visits",
    labelnames=("gender",),  # 'M' or 'F'
)
HAND_WASHING = Counter(
    "restaurant_hand_washing_total",
    "Number of times hand washing is detected",
    labelnames=("gender",),  # 'M' or 'F'
)

# Prometheus metrics
ORDER_COUNT = Counter(
    "fastfood_orders_total",
    "Total orders generated for the lunch window.",
    labelnames=("item",),
)
OVERALL_AVERAGE_TOTAL_TIME = Gauge(
    "fastfood_overall_average_total_milliseconds",
    "Average total time (queue + processing) across all orders regardless of type (in milliseconds).",
    labelnames=(),  # No labels since this is combined across all types
)
OVERALL_AVERAGE_PROCESS_TIME = Gauge(
    "fastfood_overall_average_process_milliseconds",
    "Average processing time across all machine types combined (in milliseconds).",
    labelnames=(),  # No labels since this is combined across all types
)
AVERAGE_TOTAL_TIME = Gauge(
    "fastfood_average_total_milliseconds",
    "Average total time from order creation to completion (queue + processing) in milliseconds.",
    labelnames=("item",),
)
TOTAL_TIME_MS = Histogram(
    "fastfood_total_time_milliseconds",
    "Total time from order creation to completion (queue + processing) in milliseconds.",
    labelnames=("item",),
    buckets=(0, 1000, 3000, 5000, 10000, 15000, 30000, float("inf")),  # in ms
)
P99_TOTAL_TIME = Gauge(
    "fastfood_p99_total_milliseconds",
    "99th percentile of total time (queue + processing) in milliseconds",
    labelnames=("item",),
)
P99_PROCESS_TIME = Gauge(
    "fastfood_p99_process_milliseconds",
    "99th percentile of processing time in milliseconds",
    labelnames=("item",),
)
ORDER_WAIT_MS = Histogram(
    "fastfood_order_wait_milliseconds",
    "Queue wait time before a machine picks an order (in milliseconds).",
    labelnames=("item",),
    buckets=(0, 1000, 3000, 5000, 10000, 15000, 30000, float("inf")),  # in ms
)
ORDER_PROCESS_MS = Histogram(
    "fastfood_order_processing_milliseconds",
    "Processing duration from start to finish (in milliseconds).",
    labelnames=("item",),
    buckets=(8000, 10000, 12000, 15000, 17000, 18000, 19000, 20000, 22000, 25000, 30000, 35000, 40000, 45000, float("inf")),  # in ms
)
PROCESS_TIME_SLIDING_MS = Histogram(
    "fastfood_process_time_sliding_milliseconds",
    "Processing time in sliding window for percentile calculation (in milliseconds).",
    labelnames=("item",),
    buckets=(8000, 10000, 12000, 15000, 17000, 18000, 19000, 20000, 22000, 25000, 30000, 35000, 40000, 45000, float("inf")),  # in ms
)
SLOW_ORDERS = Counter(
    "fastfood_slow_orders_total",
    "Total number of orders that took more than 30000ms (30 seconds) to process.",
    labelnames=("item",),
)
TOTAL_ORDERS = Gauge(
    "fastfood_orders_generated",
    "Number of orders generated for the simulation window.",
)
QUEUED_ORDERS = Gauge(
    "fastfood_queued_orders",
    "Number of orders waiting for a free machine.",
    labelnames=("item",),
)
BUSY_MACHINES = Gauge(
    "fastfood_busy_machines",
    "Number of machines currently processing orders.",
    labelnames=("item",),
)
AVERAGE_PROCESS_TIME = Gauge(
    "fastfood_average_process_milliseconds",
    "Average processing time for active orders (in milliseconds).",
    labelnames=("item",),
)
SLOW_ORDER_PERCENTAGE = Gauge(
    "fastfood_slow_orders_percentage",
    "Percentage of orders that are considered slow (>300ms) in the last 20 seconds.",
    labelnames=("item",),
)

def update_restaurant_metrics():
    """Update various restaurant environmental and facility metrics."""
    # Temperature varies slowly, add small random changes
    current_temp = AMBIENT_TEMP._value or 22.0  # Default start temp
    temp_change = random.uniform(-0.5, 0.5)
    new_temp = max(TEMPERATURE_RANGE[0], min(TEMPERATURE_RANGE[1], current_temp + temp_change))
    AMBIENT_TEMP.set(new_temp)
    
    # Noise level varies more dramatically with customer activity
    noise = random.uniform(*NOISE_LEVEL_RANGE)
    if random.random() < 0.1:  # 10% chance of a noise spike
        noise += random.uniform(5, 15)
    NOISE_LEVEL.set(noise)
    
    # Power usage fluctuates with equipment activity
    current_power = POWER_USAGE._value or 10000  # Default start power
    power_change = random.uniform(-500, 500)
    if random.random() < 0.05:  # 5% chance of power spike
        power_change += 2000
    new_power = max(POWER_USAGE_RANGE[0], min(POWER_USAGE_RANGE[1], current_power + power_change))
    POWER_USAGE.set(new_power)
    
    # Ice cream machine temperature
    current_ice_temp = ICE_CREAM_TEMP._value or -20  # Default start temp
    temp_drift = random.uniform(-0.2, 0.2)
    if random.random() < 0.01:  # 1% chance of defrost cycle
        temp_drift += 2
    new_ice_temp = max(ICE_CREAM_TEMP_RANGE[0], min(ICE_CREAM_TEMP_RANGE[1], current_ice_temp + temp_drift))
    ICE_CREAM_TEMP.set(new_ice_temp)
    
    # Bathroom metrics
    for gender in ['M', 'F']:
        # Update occupancy (some people leave, new people enter)
        current_occupancy = BATHROOM_OCCUPANCY.labels(gender=gender)._value or 0
        occupancy_change = random.randint(-1, 1)
        if random.random() < 0.3:  # 30% chance of additional movement
            occupancy_change += random.randint(-1, 1)
        new_occupancy = max(0, min(BATHROOM_CAPACITY, int(current_occupancy + occupancy_change)))
        BATHROOM_OCCUPANCY.labels(gender=gender).set(new_occupancy)
        
        # Update queue based on occupancy
        current_queue = BATHROOM_QUEUE.labels(gender=gender)._value or 0
        if new_occupancy >= BATHROOM_CAPACITY:
            queue_change = random.randint(0, 2)  # Queue grows when full
        else:
            queue_change = random.randint(-1, 0)  # Queue shrinks when space available
        new_queue = max(0, int(current_queue + queue_change))
        BATHROOM_QUEUE.labels(gender=gender).set(new_queue)
        
        # Count visits
        if occupancy_change > 0:
            BATHROOM_VISITS.labels(gender=gender).inc(occupancy_change)
            # 80% chance of hand washing for each new visitor
            for _ in range(occupancy_change):
                if random.random() < 0.8:
                    HAND_WASHING.labels(gender=gender).inc()

class OrderSimulator:
    def __init__(self):
        self.active_orders: List[Order] = []
        self.total_orders: int = 0
        self.busy_machines: Dict[str, int] = defaultdict(int)
        self.processing_times: Dict[str, List[tuple[float, float]]] = defaultdict(list)
        self.faulty_machine: bool = False
        self.start_time: float = time.time() * 1000  # Start time in milliseconds
    
    def _start_processing(self, order: Order) -> bool:
        if not order.queued:
            return False
            
        item = order.item
        if self.busy_machines[item] >= MACHINES[item]:
            return False
            
        order.queued = False
        order.start_time = time.time() * 1000  # Convert to milliseconds
            
        self.busy_machines[item] += 1
        return True
    
    def generate_orders(self):
        num_orders = random.randint(*ORDERS_PER_INTERVAL)
        current_time = time.time() * 1000  # Convert to milliseconds
        
        for _ in range(num_orders):
            item = random.choice(["fries", "milkshake"])
            # 5% chance of having a +180ms processing time, but only after main() has
            # been running for at least 60 seconds. Use PROGRAM_START_MS as the
            # universal program start timestamp (in milliseconds).
            program_running_ms = (time.time() * 1000 - PROGRAM_START_MS) if PROGRAM_START_MS else 0
            if program_running_ms >= 100_000 and random.random() < 0.05:
                proc_time = random.uniform(*PROCESSING_TIMES[item]) + 180
            else:
                proc_time = random.uniform(*PROCESSING_TIMES[item])
            
            order = Order(
                item=item,
                processing_time=proc_time,
                start_time=current_time,
                created_time=current_time
            )
            
            self.active_orders.append(order)
            self.total_orders += 1
            ORDER_COUNT.labels(item=item).inc()
            
    def update_metrics(self):
        # Process queued orders if machines are available
        for order in self.active_orders:
            if order.queued:
                self._start_processing(order)
        
        # Handle completed orders
        completed_orders = []
        for order in self.active_orders:
            if order.is_completed:
                completed_orders.append(order)
                if not order.queued:
                    self.busy_machines[order.item] -= 1
                    process_time = order.elapsed_time
                    total_time = time.time() * 1000 - order.created_time
                    
                    # Record processing time in both histograms
                    ORDER_PROCESS_MS.labels(item=order.item).observe(process_time)
                    PROCESS_TIME_SLIDING_MS.labels(item=order.item).observe(process_time)
                    TOTAL_TIME_MS.labels(item=order.item).observe(total_time)
                    
                    # Track slow orders (over 400ms processing time)
                    if total_time > 400:
                        SLOW_ORDERS.labels(item=order.item).inc()
                    
                    # Keep track of recent processing times (last 20 seconds)
                    current_time = time.time() * 1000
                    self.processing_times[order.item].append((current_time, process_time))
                    # Remove times older than 10 seconds (10000ms)
                    self.processing_times[order.item] = [
                        (t, p) for t, p in self.processing_times[order.item] 
                        if current_time - t <= 2000
                    ]
                
        for order in completed_orders:
            self.active_orders.remove(order)
        
        # Update metrics
        TOTAL_ORDERS.set(self.total_orders)
        current_time = time.time() * 1000
        
        for item in PROCESSING_TIMES:
            # Count queued orders
            queued = sum(1 for o in self.active_orders if o.item == item and o.queued)
            QUEUED_ORDERS.labels(item=item).set(queued)
            
            # Count busy machines
            BUSY_MACHINES.labels(item=item).set(self.busy_machines[item])
            
            # Get processing times for active orders
            active_process_times = [o.elapsed_time for o in self.active_orders 
                                  if o.item == item and not o.queued]
            recent_process_times = [p for t, p in self.processing_times[item] 
                                  if current_time - t <= 100]  # 20 second window
            
            # Get total times (queue + processing) for all orders
            active_total_times = [time.time() * 1000 - o.created_time 
                                for o in self.active_orders if o.item == item]
            
            # Combine active and recent times
            all_process_times = active_process_times + recent_process_times
            
            # Get all active and completed times
            all_process_times = active_process_times + recent_process_times
            all_total_times = active_total_times
            
            # Calculate metrics if we have data
            if all_process_times or all_total_times:
                # Calculate metrics for processing times
                if all_process_times:
                    avg_process_time = sum(all_process_times) / len(all_process_times)
                    AVERAGE_PROCESS_TIME.labels(item=item).set(avg_process_time)
                    
                    sorted_process = sorted(all_process_times)
                    if len(sorted_process) > 1:  # Need at least 2 samples for p99
                        p99_process_index = int(len(sorted_process) * 0.99)
                        p99_process = sorted_process[p99_process_index]
                        P99_PROCESS_TIME.labels(item=item).set(p99_process)
                
                # Calculate metrics for total times
                if all_total_times:
                    avg_total = sum(all_total_times) / len(all_total_times)
                    AVERAGE_TOTAL_TIME.labels(item=item).set(avg_total)
                    
                    sorted_total = sorted(all_total_times)
                    if len(sorted_total) > 1:  # Need at least 2 samples for p99
                        p99_total_index = int(len(sorted_total) * 0.99)
                        p99_total = sorted_total[p99_total_index]
                        P99_TOTAL_TIME.labels(item=item).set(p99_total)
                
                # Calculate percentage of slow orders based on processing times
                if all_process_times:
                    slow_count = sum(1 for t in all_process_times if t > 300)
                    slow_percentage = (slow_count / len(all_process_times)) * 100
                    SLOW_ORDER_PERCENTAGE.labels(item=item).set(slow_percentage)
                
            else:
                # Reset all metrics when no data is available
                AVERAGE_PROCESS_TIME.labels(item=item).set(0)
                P99_PROCESS_TIME.labels(item=item).set(0)
                AVERAGE_TOTAL_TIME.labels(item=item).set(0)
                P99_TOTAL_TIME.labels(item=item).set(0)
                SLOW_ORDER_PERCENTAGE.labels(item=item).set(0)
        
        # Calculate overall averages across all types
        # For processing time
        all_active_process_times = [o.elapsed_time for o in self.active_orders if not o.queued]
        all_recent_process_times = []
        for item in PROCESSING_TIMES:
            all_recent_process_times.extend([p for t, p in self.processing_times[item] 
                                          if current_time - t <= 2000])
        
        # For total time (queue + processing)
        all_total_times = [time.time() * 1000 - o.created_time 
                          for o in self.active_orders]  # Include all orders
        
        # Calculate and set overall averages
        all_processing_times = all_active_process_times + all_recent_process_times
        if all_processing_times:
            overall_process_avg = sum(all_processing_times) / len(all_processing_times)
            OVERALL_AVERAGE_PROCESS_TIME.set(overall_process_avg)
        else:
            OVERALL_AVERAGE_PROCESS_TIME.set(0)
            
        if all_total_times:
            overall_total_avg = sum(all_total_times) / len(all_total_times)
            OVERALL_AVERAGE_TOTAL_TIME.set(overall_total_avg)
        else:
            OVERALL_AVERAGE_TOTAL_TIME.set(0)

def main() -> None:
    random.seed()
    # Initialize the global program start timestamp so other parts of the
    # program can check how long main has been running.
    global PROGRAM_START_MS
    PROGRAM_START_MS = time.time() * 1000

    simulator = OrderSimulator()
    
    start_http_server(EXPORT_PORT)
    print(f"Order metrics exporter listening on port {EXPORT_PORT}")
    print("Press Ctrl+C to exit")

    try:
        while True:
            simulator.generate_orders()
            simulator.update_metrics()
            update_restaurant_metrics()  # Update our fun random metrics
            time.sleep(INTERVAL_MS / 1000)  # Convert ms to seconds for sleep
    except KeyboardInterrupt:
        print("\nOrder metrics exporter exiting.")

if __name__ == "__main__":

    main()
