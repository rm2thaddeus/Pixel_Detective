'use client';

import { TimelineExperience } from '../TimelineExperience';

export default function SvgTimelinePage() {
  return (
    <TimelineExperience
      initialEngine="svg"
      allowEngineSwitch={false}
      alternateEngineHref="/dev-graph/timeline/webgl"
      alternateEngineLabel="Try the WebGL2 renderer"
    />
  );
}
