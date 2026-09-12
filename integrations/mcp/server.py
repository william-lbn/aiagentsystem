try:
    from mcp.server.fastmcp import FastMCP
except ImportError: raise SystemExit("SKIP: pip install 'mcp>=2,<3'")
mcp=FastMCP('agentlab-local')
@mcp.tool()
def add(a:int,b:int)->int: return a+b
if __name__=='__main__': mcp.run()
