"""RightFit's checks engine on Cloudflare: a Python Worker that only the site's Worker can call (it has no address of
its own). It answers with app/engine.py, the laptop's own code; see that file for what a request holds."""
import json

from workers import Response, WorkerEntrypoint

from app.engine import handle

JSON = {"Content-Type": "application/json"}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        try:
            body = json.loads(await request.text())
            return Response(json.dumps(handle(body), ensure_ascii=False), headers=JSON)
        except ValueError as e:   # the laptop's own words on what is wrong, e.g. a rule's limit that is not a number
            return Response(json.dumps({"error": str(e)}), status=400, headers=JSON)
        except (KeyError, TypeError, StopIteration, IndexError, AttributeError) as e:
            return Response(json.dumps({"error": f"The request did not fit ({type(e).__name__}: {e})."}), status=400, headers=JSON)
