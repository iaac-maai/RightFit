// Adding a package on the site: its form and attachments go, one file at a time, into the project's private storage
// (worker/upload.ts). The package then waits to be read; its review appears once RightFit's reader has read it.
import { useState, type FormEvent } from "react";
import { post } from "../api";
import { plural } from "../format";
import { Modal } from "../ui";

const ACCEPT = ".pdf,.xls,.xlsx,.doc,.docx,.jpg,.jpeg,.png";

export function AddPackage({ projectId, code, open, onClose, onDone }: {
  projectId: string; code?: string; open: boolean; onClose: () => void; onDone: (code: string) => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState("");
  const [problem, setProblem] = useState("");

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!files.length) { setProblem("Choose the form and its attachments."); return; }
    const form = String(new FormData(e.currentTarget).get("form") ?? "");
    setProblem("");
    try {
      setBusy("Making the package…");
      const into = code ?? (await post<{ code: string }>(`/api/projects/${projectId}/packages/new`, { form })).code;
      for (const [i, f] of files.entries()) {
        setBusy(`Sending ${i + 1} of ${files.length}: ${f.name}`);
        const res = await fetch(`/api/projects/${projectId}/packages/${into}/upload/${encodeURIComponent(f.name)}`, {
          method: "PUT", body: f, credentials: "same-origin", headers: { "Content-Type": f.type || "application/octet-stream" },
        });
        if (!res.ok) {
          const said = (await res.json().catch(() => ({}))) as { error?: string };
          throw new Error(`${f.name}: ${said.error ?? `the server answered ${res.status}`}`);
        }
      }
      setFiles([]);
      onDone(into);
    } catch (err) {
      setProblem(`${(err as Error).message} The files sent before it are kept; send the rest again.`);
    } finally {
      setBusy("");
    }
  };

  return (
    <Modal open={open} onClose={() => (busy ? undefined : onClose())} title={code ? `Add files to ${code}` : "Add a package"}>
      <form className="stack" onSubmit={(e) => void submit(e)}>
        <p className="fine">
          The MAF form and every attachment: PDF, Excel, Word or images, up to 60 MB each. They go into this project's private
          storage. The package then waits to be read: RightFit's reader reads it, and its review appears here.
        </p>
        {!code && (
          <label className="field"><span className="lab">Form number, if you know it</span>
            <input type="text" name="form" maxLength={40} placeholder="e.g. IS 016" autoComplete="off" />
          </label>
        )}
        <label className="field"><span className="lab">Files</span>
          <input type="file" multiple accept={ACCEPT} onChange={(e) => setFiles([...(e.target.files ?? [])])} />
        </label>
        {files.length > 0 && <p className="fine">{plural(files.length, "file", "files")}, {Math.ceil(files.reduce((n, f) => n + f.size, 0) / 1048576)} MB</p>}
        {busy && <p className="fine" role="status">{busy}</p>}
        {problem && <p className="err" role="alert">{problem}</p>}
        <div className="actions">
          <button type="submit" className="btn p" disabled={Boolean(busy)}>{code ? "Send the files" : "Add the package"}</button>
          <button type="button" className="link" disabled={Boolean(busy)} onClick={onClose}>Cancel</button>
        </div>
      </form>
    </Modal>
  );
}
