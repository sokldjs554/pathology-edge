# Linked pathology workbench

The user selected pathology workbench, synchronized medical multiview, and linked image/cell data, and explicitly requested implementation with a visibly different layout from the previous version.

Use a light slide browser and inspector around a charcoal synchronized viewer. Replace the narrow thumbnail strip with readable slide rows and a persistent overview. Add an actual candidate table below the viewer; selecting a row uses the existing candidate coordinates and opens its details. Provide per-pane maximize/restore, a direct pan/select tool, and a source-image crop for the selected candidate. Preserve boundary cases, stored metrics, scope explanations, raw/kept relationships, and WSI/IHC links. Restrict styling to the boundary workbench so other pages keep their working behavior.

Alternatives considered: recoloring the existing layout does not meet the user's request; a narrative-only page sacrifices direct inspection. Chosen: a reorganized working viewer with a linked object dock. No new model runs, synthetic images, clinical claims, or changes to user-owned algorithms.

Use existing static HTML/CSS/JS and exported data; no production dependencies. Keep the site ID and public audience. Publish the completed change when source/hosting tools allow. This session has no managed browser tool; do not claim new visual/browser QA or user verification.
