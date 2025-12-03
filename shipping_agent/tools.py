import logging
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger("shipping_agent.tools")

LARGE_ORDER_THRESHOLD = 5

def place_shipping_order(
    num_containers: int, destination: str, tool_context: ToolContext
) -> dict:
    """
    Places a shipping order. Requires approval if ordering more than 5 containers.

    Args:
        num_containers: Number of containers to ship
        destination: Shipping destination
        tool_context: ADK context for handling approval state

    Returns:
        Dictionary with order status
    """
    logger.info(f"📦 Tool called: place_shipping_order(num={num_containers}, dest={destination})")

    # -----------------------------------------------------------------------------------------------
    # SCENARIO 1: Small orders (<=5 containers) auto-approve
    # -----------------------------------------------------------------------------------------------
    if num_containers <= LARGE_ORDER_THRESHOLD:
        logger.info("✅ Small order auto-approved.")
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-AUTO",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order auto-approved: {num_containers} containers to {destination}",
        }

    # -----------------------------------------------------------------------------------------------
    # SCENARIO 2: Large order - FIRST CALL (Pause)
    # -----------------------------------------------------------------------------------------------
    # tool_context.tool_confirmation is None on the first run
    if not tool_context.tool_confirmation:
        logger.warning(f"⚠️ Large order detected ({num_containers} > {LARGE_ORDER_THRESHOLD}). Requesting approval...")
        
        # Request confirmation from the system/user
        tool_context.request_confirmation(
            hint=f"⚠️ Large order: {num_containers} containers to {destination}. Do you want to approve?",
            payload={"num_containers": num_containers, "destination": destination},
        )
        
        # Return pending status to the Agent (Agent will pause after this)
        return {
            "status": "pending",
            "message": f"Order for {num_containers} containers requires approval",
        }

    # -----------------------------------------------------------------------------------------------
    # SCENARIO 3: Large order - RESUMED CALL (Resume)
    # -----------------------------------------------------------------------------------------------
    # tool_context.tool_confirmation contains the result from the human
    logger.info("🔄 Tool resumed with confirmation result.")
    
    if tool_context.tool_confirmation.confirmed:
        logger.info("✅ Order approved by human.")
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-HUMAN",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order approved: {num_containers} containers to {destination}",
        }
    else:
        logger.info("❌ Order rejected by human.")
        return {
            "status": "rejected",
            "message": f"Order rejected: {num_containers} containers to {destination}",
        }
