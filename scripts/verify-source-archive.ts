import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

type ArchiveObject = {
  source: string;
  sha256: `sha256:${string}`;
  bytes: number;
  mirror: string;
};

type ArchiveManifest = {
  schema: "erdos-frontier.source-archive.v1";
  source_repository: string;
  objects: ArchiveObject[];
};

const root = resolve(import.meta.dir, "..");
const manifestPath = resolve(
  root,
  "sources/archive/vela-internal/manifest.json",
);
const manifest = JSON.parse(
  await readFile(manifestPath, "utf8"),
) as ArchiveManifest;

if (manifest.schema !== "erdos-frontier.source-archive.v1") {
  throw new Error(`unexpected archive schema: ${manifest.schema}`);
}

const seenSources = new Set<string>();
const seenMirrors = new Set<string>();

for (const object of manifest.objects) {
  if (seenSources.has(object.source)) {
    throw new Error(`duplicate source identity: ${object.source}`);
  }
  if (seenMirrors.has(object.mirror)) {
    throw new Error(`duplicate mirror path: ${object.mirror}`);
  }
  seenSources.add(object.source);
  seenMirrors.add(object.mirror);

  const bytes = await readFile(resolve(root, object.mirror));
  const digest = `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
  if (bytes.byteLength !== object.bytes) {
    throw new Error(
      `${object.mirror}: expected ${object.bytes} bytes, got ${bytes.byteLength}`,
    );
  }
  if (digest !== object.sha256) {
    throw new Error(
      `${object.mirror}: expected ${object.sha256}, got ${digest}`,
    );
  }
}

const referenceFiles = ["sources/recovered-attempts.yaml"];
const referencedSources = new Set<string>();
const sourcePattern =
  /vela-science\/vela-internal@[0-9a-f]{40}:[^@"'\s]+?(?=#|@sha256:|["'\s])/g;

for (const referenceFile of referenceFiles) {
  const content = await readFile(resolve(root, referenceFile), "utf8");
  for (const match of content.matchAll(sourcePattern)) {
    referencedSources.add(match[0]);
  }
}

const missingMirrors = [...referencedSources].filter(
  (source) => !seenSources.has(source),
);
const unreferencedMirrors = [...seenSources].filter(
  (source) => !referencedSources.has(source),
);
if (missingMirrors.length > 0) {
  throw new Error(
    `historical sources missing public mirrors: ${missingMirrors.join(", ")}`,
  );
}
if (unreferencedMirrors.length > 0) {
  throw new Error(
    `archive contains unreferenced mirrors: ${unreferencedMirrors.join(", ")}`,
  );
}

console.log(
  JSON.stringify({
    ok: true,
    schema: manifest.schema,
    source_repository: manifest.source_repository,
    object_count: manifest.objects.length,
    referenced_object_count: referencedSources.size,
  }),
);
