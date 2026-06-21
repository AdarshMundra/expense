from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.database.session import init_db, close_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
# MCP uses stdout for JSON-RPC — silence SQLAlchemy so it never touches stdout
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown logic."""
    logger.info("Starting Expense MCP server...")

    # Initialize database
    await init_db()
    logger.info("Database initialized.")

    # Seed default categories
    from app.database.session import get_session
    from app.services.category_service import category_service
    async with get_session() as session:
        await category_service.seed_default_categories(session)
    logger.info("Default categories seeded.")

    yield

    # Shutdown
    await close_db()
    logger.info("Expense MCP server stopped.")


# Create the FastMCP instance
mcp = FastMCP("Expense Tracker", lifespan=lifespan)

# Register all tools
from app.tools import transaction_tools, analytics_tools, category_tools, budget_tools

transaction_tools.register_tools(mcp)
analytics_tools.register_tools(mcp)
category_tools.register_tools(mcp)
budget_tools.register_tools(mcp)

# Register prompts
from app.prompts import prompts

prompts.register_prompts(mcp)

# Register resources
from app.resources import resources

resources.register_resources(mcp)

logger.info("All tools, prompts, and resources registered.")


def main() -> None:
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
