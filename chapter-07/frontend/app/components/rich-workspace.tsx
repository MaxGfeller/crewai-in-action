import { FileText } from "lucide-react";

import { SurfaceCard } from "./surface-card";
import type { UiSurface } from "./types";

export function RichWorkspace({ surfaces }: { surfaces: UiSurface[] }) {
  return (
    <section className="workspacePanel">
      <div className="workspacePanelHeader">
        <div>
          <p className="eyebrow">AG-UI state</p>
          <h2>Rich workspace</h2>
        </div>
        <span className="mono">{surfaces.length} surfaces</span>
      </div>
      <div className="surfaceStack">
        {surfaces.length === 0 ? (
          <div className="emptyCanvas">
            <FileText size={28} />
            <h2>Rich surfaces appear here</h2>
            <p>Cards from custom AG-UI events render beside the transcript.</p>
          </div>
        ) : (
          surfaces.map((surface) => (
            <SurfaceCard key={surface.surface_id} surface={surface} />
          ))
        )}
      </div>
    </section>
  );
}
