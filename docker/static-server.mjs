import { createReadStream, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, resolve, sep } from "node:path";

const root = resolve(process.env.WEB_ROOT || "/srv/site");
const port = Number(process.env.PORT || 8080);

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".stl", "model/stl"],
]);

function safePath(url) {
  const pathname = decodeURIComponent(new URL(url, "http://localhost").pathname);
  const relative = pathname === "/" ? "acoustics.html" : pathname.replace(/^\/+/, "");
  const candidate = resolve(root, relative);
  if (candidate !== root && !candidate.startsWith(`${root}${sep}`)) return null;
  return candidate;
}

const server = createServer((request, response) => {
  if (request.url === "/healthz") {
    response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ status: "ok" }));
    return;
  }

  const path = safePath(request.url || "/");
  if (!path) {
    response.writeHead(400);
    response.end("Bad request");
    return;
  }

  try {
    if (!statSync(path).isFile()) throw new Error("not a file");
  } catch {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }

  response.writeHead(200, {
    "cache-control": "no-store",
    "content-type": contentTypes.get(extname(path).toLowerCase()) || "application/octet-stream",
    "cross-origin-embedder-policy": "require-corp",
    "cross-origin-opener-policy": "same-origin",
    "x-content-type-options": "nosniff",
  });
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  createReadStream(path).pipe(response);
});

server.listen(port, "0.0.0.0", () => {
  console.log(`AgnuQuena web server listening on http://0.0.0.0:${port}`);
});
