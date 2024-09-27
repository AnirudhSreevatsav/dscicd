from flask import Blueprint, request, current_app
from app.services.ml_service import MLService
from flask_cors import cross_origin
import threading
import asyncio

ml_controller = Blueprint("ml_controller", __name__)

current_thread = None
stop_event = threading.Event()


def run_async_task(valid_data, result, app, stop_event):
    with app.app_context():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run_with_interrupt_check():
            task = asyncio.create_task(MLService.stimulator(valid_data, stop_event))
            while not task.done():
                if stop_event.is_set():
                    task.cancel()
                    break
                await asyncio.sleep(0.1)
            if not task.cancelled():
                result["response"] = await task

        loop.run_until_complete(run_with_interrupt_check())
        loop.close()


@ml_controller.route("/stimulator", methods=["POST"])
@cross_origin()
def stimulator():
    global current_thread, stop_event
    valid_data = request.get_json()
    result = {"response": None}

    stop_event.clear()

    try:
        app = current_app._get_current_object()
        current_thread = threading.Thread(
            target=run_async_task, args=(valid_data, result, app, stop_event)
        )
        current_thread.start()
        current_thread.join()

        if result["response"] is None:
            return ({"error": "No response from ML service"}), 500
        return result["response"]
    except Exception as e:
        print(f"Error in stimulator controller: {e}")
        return ({"error": str(e)}), 500


@ml_controller.route("/stop-stimulator", methods=["POST"])
@cross_origin()
def stop_stimulator():
    global current_thread, stop_event
    if current_thread and current_thread.is_alive():
        stop_event.set()
        current_thread.join(timeout=2.0)
        if current_thread.is_alive():
            return (
                {"message": "Thread is still running and cannot be stopped immediately"}
            ), 202
        else:
            current_thread = None
            return ({"message": "Thread stopped successfully"}), 200
    else:
        return ({"message": "No active thread to stop"}), 200


@ml_controller.route("/analyse-on-call", methods=["POST"])
def analyse_on_call():
    response = MLService.analyse_on_call(request.get_json())
    return response