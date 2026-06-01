import fs from "node:fs";
import path from "node:path";
import sharp from "sharp";

const outputPath = process.argv[2] ?? path.resolve("build/icon-master.png");
const outputDir = path.dirname(outputPath);
fs.mkdirSync(outputDir, { recursive: true });

const svg = `
<svg width="1024" height="1024" viewBox="0 0 1024 1024" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="164" y1="120" x2="860" y2="920" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0FCAFF"/>
      <stop offset="0.48" stop-color="#1261E8"/>
      <stop offset="1" stop-color="#13215F"/>
    </linearGradient>
    <radialGradient id="warmGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(748 168) rotate(118) scale(356 360)">
      <stop stop-color="#FDE68A" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#FDE68A" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="coolGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(260 822) rotate(-48) scale(424 372)">
      <stop stop-color="#67E8F9" stop-opacity="0.38"/>
      <stop offset="1" stop-color="white" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="calendarHeader" x1="336" y1="238" x2="768" y2="390" gradientUnits="userSpaceOnUse">
      <stop stop-color="#06B6D4"/>
      <stop offset="1" stop-color="#2563EB"/>
    </linearGradient>
    <linearGradient id="assignmentCard" x1="174" y1="310" x2="418" y2="598" gradientUnits="userSpaceOnUse">
      <stop stop-color="#FFFFFF"/>
      <stop offset="1" stop-color="#DFF8FF"/>
    </linearGradient>
    <filter id="cardShadow" x="80" y="106" width="864" height="820" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
      <feDropShadow dx="0" dy="26" stdDeviation="32" flood-color="#020617" flood-opacity="0.38"/>
    </filter>
    <filter id="softShadow" x="70" y="220" width="420" height="460" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
      <feDropShadow dx="0" dy="20" stdDeviation="22" flood-color="#020617" flood-opacity="0.28"/>
    </filter>
  </defs>
  <rect width="1024" height="1024" rx="224" fill="#020617"/>
  <g filter="url(#cardShadow)">
    <rect x="96" y="96" width="832" height="832" rx="212" fill="url(#bg)"/>
    <rect x="96" y="96" width="832" height="832" rx="212" fill="url(#warmGlow)"/>
    <rect x="96" y="96" width="832" height="832" rx="212" fill="url(#coolGlow)"/>
    <g opacity="0.16" stroke="#E0F2FE" stroke-width="18" stroke-linecap="round">
      <path d="M210 248H814"/>
      <path d="M210 408H814"/>
      <path d="M210 568H814"/>
      <path d="M210 728H814"/>
      <path d="M286 188V828"/>
      <path d="M446 188V828"/>
      <path d="M606 188V828"/>
      <path d="M766 188V828"/>
    </g>

    <g filter="url(#softShadow)">
      <rect x="164" y="316" width="300" height="332" rx="58" fill="url(#assignmentCard)"/>
      <rect x="164" y="316" width="300" height="92" rx="58" fill="#0F172A"/>
      <rect x="164" y="374" width="300" height="40" fill="#0F172A"/>
      <text x="218" y="378" fill="#67E8F9" font-family="Arial, sans-serif" font-size="52" font-weight="800" letter-spacing="2">LMS</text>
      <circle cx="226" cy="468" r="15" fill="#2563EB"/>
      <rect x="260" y="452" width="144" height="28" rx="14" fill="#0F172A" fill-opacity="0.82"/>
      <rect x="260" y="492" width="110" height="22" rx="11" fill="#0F172A" fill-opacity="0.28"/>
      <circle cx="226" cy="552" r="15" fill="#2563EB"/>
      <rect x="260" y="536" width="154" height="28" rx="14" fill="#0F172A" fill-opacity="0.82"/>
      <rect x="260" y="576" width="126" height="22" rx="11" fill="#0F172A" fill-opacity="0.28"/>
    </g>

    <path d="M430 304C516 206 678 196 764 288" stroke="#A7F3D0" stroke-width="36" stroke-linecap="round"/>
    <path d="M760 226L790 324L688 309" stroke="#A7F3D0" stroke-width="36" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M594 802C474 822 374 754 344 650" stroke="#67E8F9" stroke-width="34" stroke-linecap="round"/>
    <path d="M408 672L332 624L308 714" stroke="#67E8F9" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>

    <rect x="354" y="230" width="492" height="596" rx="82" fill="#F8FAFC"/>
    <rect x="354" y="230" width="492" height="156" rx="82" fill="url(#calendarHeader)"/>
    <rect x="354" y="322" width="492" height="82" fill="url(#calendarHeader)"/>
    <rect x="440" y="176" width="78" height="126" rx="32" fill="#0F172A"/>
    <rect x="676" y="176" width="78" height="126" rx="32" fill="#0F172A"/>
    <rect x="455" y="184" width="48" height="96" rx="24" fill="#E0F2FE"/>
    <rect x="691" y="184" width="48" height="96" rx="24" fill="#E0F2FE"/>
    <text x="436" y="326" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="64" font-weight="900" letter-spacing="4">DUE</text>

    <g fill="#DCEBFF">
      <rect x="420" y="456" width="72" height="64" rx="20"/>
      <rect x="520" y="456" width="72" height="64" rx="20"/>
      <rect x="620" y="456" width="72" height="64" rx="20"/>
      <rect x="720" y="456" width="72" height="64" rx="20"/>
      <rect x="420" y="548" width="72" height="64" rx="20"/>
      <rect x="520" y="548" width="72" height="64" rx="20"/>
      <rect x="620" y="548" width="72" height="64" rx="20"/>
      <rect x="720" y="548" width="72" height="64" rx="20"/>
      <rect x="420" y="640" width="72" height="64" rx="20"/>
      <rect x="520" y="640" width="72" height="64" rx="20"/>
    </g>
    <rect x="620" y="640" width="172" height="64" rx="22" fill="#2563EB"/>
    <text x="664" y="690" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="46" font-weight="900">7</text>

    <circle cx="750" cy="720" r="112" fill="#14B8A6"/>
    <circle cx="750" cy="720" r="112" stroke="#ECFEFF" stroke-opacity="0.78" stroke-width="14"/>
    <path d="M694 718L735 758L814 674" stroke="#FFFFFF" stroke-width="38" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>
`;

await sharp(Buffer.from(svg))
  .png()
  .toFile(outputPath);

console.log(`아이콘 마스터 PNG 생성 완료: ${outputPath}`);
