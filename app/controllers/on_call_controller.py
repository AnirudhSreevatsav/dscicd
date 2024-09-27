from flask import Blueprint, request, jsonify
from app.services.on_call_service import OnCallService
from concurrent.futures import ThreadPoolExecutor
import threading

on_call_controller = Blueprint("on_call_controller", __name__)

thread_pool = ThreadPoolExecutor(max_workers=5)

# Global variable to store the current simulation futures
simulation_futures = {}

@on_call_controller.route("/on-call-simulation", methods=["POST"])
def on_call_simulation():
    global simulation_futures
    
    opportunity_id = request.get_json().get("opportunity_id")
    
    if opportunity_id in simulation_futures and not simulation_futures[opportunity_id].done():
        return jsonify({"error": "A simulation is already running for this opportunity"}), 400

    # Submit the simulation task to the thread pool
    future = thread_pool.submit(OnCallService.on_call_simulation, request.get_json())
    simulation_futures[opportunity_id] = future
    
    return jsonify({"message": "Simulation started"}), 202

@on_call_controller.route("/stop-on-call-simulation", methods=["POST"])
def stop_on_call_simulation():
    data = request.get_json()
    opportunity_id = data.get("opportunity_id")
    stop_all = data.get("stop_all")

    
    if opportunity_id:
        # Stop specific simulation
        if opportunity_id not in simulation_futures or simulation_futures[opportunity_id].done():
            return jsonify({"message": "No simulation is currently running for this opportunity"}), 400

        # Cancel the future if it's still running
        simulation_futures[opportunity_id].cancel()
        del simulation_futures[opportunity_id]
        return jsonify({"message": f"Simulation stopped for opportunity {opportunity_id}"}), 200
    else:

        if stop_all:
            # cancel all simulations and the delete them from taking any resources
            for future in simulation_futures.values():
                future.cancel()
            simulation_futures.clear()
            return jsonify({"message": "All simulations stopped"}), 200
        else:
            # Return all running simulation opportunity IDs        
            running_simulations = [opp_id for opp_id, future in simulation_futures.items() if not future.done()]
        return jsonify({"running_simulations": running_simulations}), 200

def run_simulation(data):
    OnCallService.on_call_simulation(data)