import fs from "node:fs";
import path from "node:path";
import sharp from "sharp";

const outputPath = process.argv[2] ?? path.resolve("build/icon-master.png");
const outputDir = path.dirname(outputPath);
fs.mkdirSync(outputDir, { recursive: true });

const svg = `
<svg width="1024" height="1024" viewBox="0 0 1024 1024" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="512" y1="96" x2="512" y2="928" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0DB7FF"/>
      <stop offset="0.5" stop-color="#0A6FE0"/>
      <stop offset="1" stop-color="#0A2F78"/>
    </linearGradient>
    <radialGradient id="glow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(511 164) rotate(90) scale(336 420)">
      <stop stop-color="white" stop-opacity="0.45"/>
      <stop offset="1" stop-color="white" stop-opacity="0"/>
    </radialGradient>
    <filter id="shadow" x="56" y="56" width="912" height="912" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
      <feDropShadow dx="0" dy="18" stdDeviation="28" flood-color="#020617" flood-opacity="0.34"/>
    </filter>
  </defs>
  <rect width="1024" height="1024" rx="224" fill="#020617"/>
  <g filter="url(#shadow)">
    <rect x="96" y="96" width="832" height="832" rx="212" fill="url(#bg)"/>
    <ellipse cx="512" cy="218" rx="340" ry="136" fill="url(#glow)"/>
    <g opacity="0.15" stroke="#E0F2FE" stroke-width="22" stroke-linecap="round">
      <path d="M220 190V840"/>
      <path d="M340 190V840"/>
      <path d="M460 190V840"/>
      <path d="M580 190V840"/>
      <path d="M700 190V840"/>
      <path d="M820 190V840"/>
      <path d="M170 220H870"/>
      <path d="M170 340H870"/>
      <path d="M170 460H870"/>
      <path d="M170 580H870"/>
      <path d="M170 700H870"/>
      <path d="M170 820H870"/>
    </g>
    <rect x="214" y="210" width="596" height="604" rx="92" fill="#F8FAFC"/>
    <rect x="214" y="608" width="596" height="206" rx="92" fill="#0A6FE0"/>
    <rect x="214" y="660" width="596" height="154" fill="#0A6FE0"/>
    <rect x="292" y="724" width="90" height="126" rx="34" fill="#0A2F78"/>
    <rect x="640" y="724" width="90" height="126" rx="34" fill="#0A2F78"/>
    <rect x="278" y="548" width="468" height="46" rx="22" fill="#E0F2FE" fill-opacity="0.88"/>

    <circle cx="307" cy="474" r="13" fill="#0A6FE0"/>
    <rect x="338" y="457" width="360" height="34" rx="17" fill="#122B55" fill-opacity="0.88"/>
    <rect x="338" y="415" width="248" height="30" rx="15" fill="#122B55" fill-opacity="0.30"/>

    <circle cx="307" cy="386" r="13" fill="#0A6FE0"/>
    <rect x="338" y="369" width="360" height="34" rx="17" fill="#122B55" fill-opacity="0.88"/>
    <rect x="338" y="327" width="270" height="30" rx="15" fill="#122B55" fill-opacity="0.30"/>

    <circle cx="307" cy="298" r="13" fill="#0A6FE0"/>
    <rect x="338" y="281" width="360" height="34" rx="17" fill="#122B55" fill-opacity="0.88"/>
    <rect x="338" y="239" width="292" height="30" rx="15" fill="#122B55" fill-opacity="0.30"/>

    <path d="M592 250L646 198L754 324" stroke="#19D6A2" stroke-width="28" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
`;

await sharp(Buffer.from(svg))
  .png()
  .toFile(outputPath);

console.log(`아이콘 마스터 PNG 생성 완료: ${outputPath}`);
