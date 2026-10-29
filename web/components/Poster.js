"use client";

import { useState } from "react";
import { initials } from "../lib/labels";

const SQUARE = ["urn:entity:podcast", "urn:entity:artist", "urn:entity:brand"];

export default function Poster({ src, name, type, size = "" }) {
  const [broken, setBroken] = useState(false);
  const shape = SQUARE.includes(type) ? "square" : "";
  const brand = type === "urn:entity:brand" ? "brand" : "";
  return (
    <span className={`poster ${shape} ${brand} ${size}`}>
      {src && !broken ? <img src={src} alt="" loading="lazy" onError={() => setBroken(true)} /> : <span className="poster-fallback">{initials(name)}</span>}
    </span>
  );
}
