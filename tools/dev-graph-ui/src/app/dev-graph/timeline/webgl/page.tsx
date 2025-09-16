'use client';

import { TimelineExperience } from '../TimelineExperience';

export default function WebglTimelinePage() {
  return (
    <TimelineExperience
      initialEngine="webgl"
      allowEngineSwitch={false}
      alternateEngineHref="/dev-graph/timeline/svg"
      alternateEngineLabel="Switch to the SVG renderer"
    />
  );
}
