"use client";

import { useEffect, useRef } from "react";
import { MotionValue, useMotionValueEvent } from "framer-motion";

interface StoryCanvasProps {
    scrollProgress: MotionValue<number>;
}

export function StoryCanvas({ scrollProgress }: StoryCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const progressRef = useRef(0);
    useMotionValueEvent(scrollProgress, "change", (latest) => {
        progressRef.current = latest;
    });

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let animationFrameId: number;
        let time = 0;

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        window.addEventListener("resize", resize);
        resize();

        // --- SYSTEMS INIT ---
        const width = window.innerWidth;
        const height = window.innerHeight;

        // Act II Variables
        const lines: {
            x: number, y: number, speed: number, offset: number,
            baseY: number, color: string
        }[] = [];
        for (let i = 0; i < 80; i++) {
            lines.push({
                x: Math.random() * width,
                y: Math.random() * height,
                speed: 0.5 + Math.random() * 2,
                offset: Math.random() * 100,
                baseY: Math.random() * height,
                color: Math.random() > 0.8 ? "#D4A853" : "#8B8E94"
            });
        }

        // Act IV: Terrain Data (Pre-calculate for consistency)
        const terrainRows = 40;
        const terrainCols = 40;
        const terrainSpacing = 50; // Tighter grid
        const terrain: { x: number, z: number, y: number, originalY: number }[] = [];

        // Populate terrain with some noise/landscape
        for (let r = 0; r < terrainRows; r++) {
            for (let c = 0; c < terrainCols; c++) {
                const x = (c - terrainCols / 2) * terrainSpacing;
                const z = (r - terrainRows / 2) * terrainSpacing;
                // Simple static noise for shape, we'll animate additional waves
                const noise = Math.sin(x * 0.02) * Math.cos(z * 0.02) * 100 +
                    Math.sin(x * 0.05 + z * 0.05) * 50;

                terrain.push({
                    x: x,
                    z: z,
                    y: noise,
                    originalY: noise
                });
            }
        }

        // Act III: Genesis Particles (Text Formation: GLOQONT)
        // We reuse these particles for Act IV transition
        const particles: {
            x: number, y: number,
            tx: number, ty: number, // Target position (Text)
            vx: number, vy: number,
            // Act II Source
            lineIndex?: number,
            lineT?: number,
            // Act IV Targets
            targetGridIndex?: number
        }[] = [];

        // Virtual Canvas for Text Sampling
        const textCanvas = document.createElement("canvas");
        textCanvas.width = width;
        textCanvas.height = height;
        const tCtx = textCanvas.getContext("2d");

        if (tCtx) {
            tCtx.fillStyle = "black";
            tCtx.fillRect(0, 0, width, height);

            // Render text to sample
            const fontSize = Math.min(width * 0.18, 200);
            tCtx.font = `900 ${fontSize}px sans-serif`;
            tCtx.textAlign = "center";
            tCtx.textBaseline = "middle";
            tCtx.fillStyle = "white";
            tCtx.fillText("GLOQONT", width / 2, height / 2);

            const idata = tCtx.getImageData(0, 0, width, height).data;
            const step = Math.max(4, Math.floor(width / 150));

            let pIndex = 0;
            for (let y = 0; y < height; y += step) {
                for (let x = 0; x < width; x += step) {
                    const alpha = idata[(y * width + x) * 4];
                    if (alpha > 128) {
                        // Assign a grid point to this particle if available
                        const gridIndex = pIndex < terrain.length ? pIndex : undefined;

                        particles.push({
                            x: Math.random() * width,
                            y: Math.random() * height,
                            tx: x,
                            ty: y,
                            vx: (Math.random() - 0.5) * 2,
                            vy: (Math.random() - 0.5) * 2,
                            lineIndex: pIndex % 80, // Distribute across lines
                            lineT: Math.random(), // Random pos on line
                            targetGridIndex: gridIndex
                        });
                        pIndex++;
                    }
                }
            }
        }

        // Ensure we have enough particles for the terrain even if text is small
        if (particles.length < terrain.length) {
            for (let i = particles.length; i < terrain.length; i++) {
                particles.push({
                    x: Math.random() * width,
                    y: Math.random() * height,
                    tx: width / 2, // Default text target center if needed, or hidden
                    ty: height / 2,
                    vx: 0, vy: 0,
                    lineIndex: i % 80,
                    lineT: Math.random(),
                    targetGridIndex: i
                });
            }
        }

        // --- RENDER LOOP ---
        const render = () => {
            time += 0.01;
            const progress = progressRef.current;
            const w = canvas.width;
            const h = canvas.height;

            // Clear Screen
            // Fade logic for trails
            ctx.fillStyle = `rgba(5, 5, 5, ${progress > 0.6 ? 0.3 : 0.2})`;
            ctx.fillRect(0, 0, w, h);

            // === ACT I & II (Simplified for brevity, ensuring they persist) ===
            // ... (Keeping logic similar to before but compacting if needed, 
            // for now explicitly re-implementing to ensure no regression)

            // Act I
            if (progress < 0.25) {
                const intensity = 1 - (progress * 5);
                if (intensity > 0) {
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(212, 168, 83, ${intensity})`;
                    ctx.lineWidth = 2;
                    const centY = h / 2;
                    ctx.moveTo(0, centY);
                    for (let x = 0; x < w; x += 10) {
                        const noise = Math.sin(x * 0.01 + time * 5) * Math.cos(x * 0.05 - time) * 50;
                        ctx.lineTo(x, centY + noise);
                    }
                    ctx.stroke();
                }
            }

            // Calculate Act II Line Positions (We need this logic for Act III morph too)
            const getLinePos = (lineIndex: number, t: number, progress: number) => {
                const line = lines[lineIndex % lines.length];
                const actProgress = Math.max(0, Math.min(1, (progress - 0.15) / 0.35));

                // Split Logic: Start at center, move to base
                // Fast split at start
                const splitFactor = Math.min(1, actProgress * 3);

                const startY = h / 2;
                const spread = (actProgress * 4);

                // Target Y morphs from center to spread
                // Weave effect
                const convergence = Math.max(0, (progress - 0.4) * 3);
                // Base target is mixed between center and baseY based on splitFactor
                const baseTargetY = (h / 2) * (1 - splitFactor) + line.baseY * splitFactor;
                const targetY = baseTargetY * (1 - convergence) + (h / 2) * convergence;

                const cp1y = startY;
                const cp2y = startY + (targetY - startY) * spread;

                // Points for Bezier
                const p0x = 0; const p0y = startY;
                const p1x = w * 0.4; const p1y = cp1y;
                const p2x = w * 0.6; const p2y = cp2y;
                const p3x = w; const p3y = targetY;

                // Cubic Bezier
                const invT = 1 - t;
                const bx = Math.pow(invT, 3) * p0x + 3 * Math.pow(invT, 2) * t * p1x + 3 * invT * Math.pow(t, 2) * p2x + Math.pow(t, 3) * p3x;
                const by = Math.pow(invT, 3) * p0y + 3 * Math.pow(invT, 2) * t * p1y + 3 * invT * Math.pow(t, 2) * p2y + Math.pow(t, 3) * p3y;

                return { x: bx, y: by };
            };

            // === ACT II: BIFURCATION (0.15 - 0.5) ===
            if (progress > 0.1 && progress < 0.55) {
                const actProgress = (progress - 0.15) / 0.35;
                const opacity = Math.min(1, Math.max(0, (progress - 0.15) * 10)) * Math.max(0, 1 - (progress - 0.35) * 15);

                // --- TRANSITION 1: IMPULSE -> BIFURCATION (Sonic Boom) ---
                const boomTime = (progress - 0.15) * 10;
                let boomRadius = 0;
                let boomOpacity = 0;

                if (boomTime > 0 && boomTime < 2) {
                    boomRadius = boomTime * w * 0.8;
                    boomOpacity = 1 - (boomTime / 2);
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(255, 255, 255, ${boomOpacity * 0.5})`;
                    ctx.lineWidth = 2 + boomTime * 10;
                    ctx.arc(w / 2, h / 2, boomRadius, 0, Math.PI * 2);
                    ctx.stroke();
                }

                if (opacity > 0) {
                    lines.forEach((line, idx) => {
                        ctx.beginPath();

                        // Dissolve parameters
                        const dissolve = Math.max(0, (progress - 0.35) * 10);
                        const isDissolving = dissolve > 0;

                        let lineOpacity = opacity;
                        if (isDissolving) {
                            lineOpacity *= (Math.random() > 0.3 ? 1 : 0.2);
                        }

                        ctx.strokeStyle = line.color === "#D4A853"
                            ? `rgba(212, 168, 83, ${lineOpacity * 0.6})`
                            : `rgba(139, 142, 148, ${lineOpacity * 0.3})`;
                        ctx.lineWidth = 1;

                        // Re-calculate bezier points for drawing
                        // We use the helper function logic but for full curve
                        // Simplified: Just use the same logic as getLinePos implies for the control points
                        const startY = h / 2;
                        const splitFactor = Math.min(1, actProgress * 3);
                        const baseTargetY = (h / 2) * (1 - splitFactor) + line.baseY * splitFactor;

                        // Convergence for end of Act II
                        const convergence = Math.max(0, (progress - 0.4) * 3);
                        const targetY = baseTargetY * (1 - convergence) + (h / 2) * convergence;
                        const spread = (actProgress * 4);

                        const cp1y = startY;
                        const cp2y = startY + (targetY - startY) * spread;

                        const p0x = 0; const p0y = startY;
                        const p1x = w * 0.4; const p1y = cp1y;
                        const p2x = w * 0.6; const p2y = cp2y;
                        const p3x = w; const p3y = targetY;

                        if (!isDissolving) {
                            ctx.moveTo(p0x, p0y);
                            ctx.bezierCurveTo(p1x, p1y, p2x, p2y, p3x, p3y);
                            ctx.stroke();
                        } else {
                            // Draw separated segments
                            const segments = 20;
                            for (let s = 0; s <= segments; s++) {
                                const t = s / segments;
                                const invT = 1 - t;
                                const bx = Math.pow(invT, 3) * p0x + 3 * Math.pow(invT, 2) * t * p1x + 3 * invT * Math.pow(t, 2) * p2x + Math.pow(t, 3) * p3x;
                                const by = Math.pow(invT, 3) * p0y + 3 * Math.pow(invT, 2) * t * p1y + 3 * invT * Math.pow(t, 2) * p2y + Math.pow(t, 3) * p3y;

                                const jitterX = (Math.random() - 0.5) * dissolve * 50;
                                const jitterY = (Math.random() - 0.5) * dissolve * 50;

                                if (Math.random() > dissolve * 0.5) {
                                    ctx.fillStyle = ctx.strokeStyle;
                                    ctx.fillRect(bx + jitterX, by + jitterY, 2, 2);
                                }
                            }
                        }
                    });

                    // Sparks
                    if (progress > 0.4) {
                        for (let s = 0; s < 10; s++) {
                            ctx.fillStyle = `rgba(212, 168, 83, ${Math.random() * opacity})`;
                            ctx.fillRect(
                                Math.random() * w,
                                h / 2 + (Math.random() - 0.5) * h * (1 - progress),
                                2, 2
                            );
                        }
                    }
                }
            }

            // === ACT III: GENESIS (THE WEAVER) (0.4 - 0.75) ===
            // Transition: Act II Lines -> Act III Text
            if (progress > 0.35 && progress < 0.75) {
                const actProgress = (progress - 0.35) / 0.40;

                // Morph Factor: 0 = Line, 1 = Text
                // Start morphing early (0.35) to catch lines
                // Full text by 0.55
                const morphT = Math.max(0, Math.min(1, (progress - 0.35) * 5));
                const ease = morphT * morphT * (3 - 2 * morphT); // Smooth step

                const opacity = Math.min(1, Math.max(0, (progress - 0.35) * 5)) * Math.max(0, 1 - (progress - 0.65) * 10);

                if (opacity > 0) {
                    ctx.lineWidth = 1;

                    particles.forEach(p => {
                        // 1. Calculate Start Point (on the Line)
                        // Use the getLinePos function defined in Act II scope logic
                        // We need the line state just before it completely fades/dissolves
                        // Let's use progress = 0.4 as reference 'freeze' point for lines, or animate them 
                        // It looks cooler if lines keep moving while particles fly off
                        // But lines fade out at 0.5. Morph starts at 0.35.
                        // So between 0.35 and 0.5, particles are leaving the lines.

                        const linePos = getLinePos(p.lineIndex !== undefined ? p.lineIndex : 0, p.lineT !== undefined ? p.lineT : 0.5, progress);

                        // 2. Define Target (Text)
                        // Swarm noise
                        const noiseX = Math.sin(time + p.y * 0.05) * 20 * (1 - ease);
                        const noiseY = Math.cos(time + p.x * 0.05) * 20 * (1 - ease);

                        const tx = p.tx + noiseX;
                        const ty = p.ty + noiseY;

                        // 3. Interpolate
                        // ease 0 -> use linePos
                        // ease 1 -> use tx, ty
                        const cx = linePos.x * (1 - ease) + tx * ease;
                        const cy = linePos.y * (1 - ease) + ty * ease;

                        // Save current pos for next frame smoothing or trails
                        p.x = cx;
                        p.y = cy;

                        // Draw
                        // Trails logic
                        const trailLen = 10 * (1 - ease) + 2;
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(212, 168, 83, ${opacity * (0.3 + 0.7 * ease)})`;

                        // Calculate vector for trail alignment? 
                        // Simple approach: drag behind velocity or just draw line to previous?
                        // For now keep simple trail length logic
                        ctx.moveTo(cx - (p.vx || 1) * trailLen, cy - (p.vy || 1) * trailLen);
                        ctx.lineTo(cx, cy);
                        ctx.stroke();
                    });
                }
            }

            // === ACT IV: TERRAIN SCANNER (0.55 - 1.0) ===


            // === ACT III -> IV TRANSITION ===
            if (progress > 0.35) {
                // Act III Opacity
                const a3Entry = Math.min(1, Math.max(0, (progress - 0.35) * 5));
                const a3Exit = Math.max(0, 1 - (progress - 0.75) * 5); // Extend exit for transition
                const a3Opacity = a3Entry * a3Exit;

                // Act IV Opacity
                const a4Entry = Math.min(1, Math.max(0, (progress - 0.6) * 5));
                const a4Opacity = a4Entry;

                // Transition Factor: 0 = Text, 1 = Terrain
                // Start transitioning around 0.65, fully terrain by 0.75
                const transT = Math.max(0, Math.min(1, (progress - 0.65) * 10));

                // Camera / Scene Params for 3D
                const cx = w / 2;
                const fieldOfView = 800;
                // Camera moves: 
                // Act IV: angled view. 
                const camY = -500 + Math.sin(time * 0.5) * 50;
                const camZ = -1000 + (progress - 0.6) * 2000; // Fly forward
                const rotX = 1.2; // Tilt down
                const rotY = time * 0.1; // Slow rotation

                // Scanner Beam Params
                const scannerZ = ((time * 400) % 3000) - 1500; // Moves back and forth or loops

                // --- Calculate Terrain Projection once per frame if needed OR per particle ---
                // We'll calculate per particle to morph them

                /* 
                   LOGIC:
                   If transT == 0: Particles stick to Text Targets (Act III behavior)
                   If transT > 0: Particles explode/move towards Terrain Targets (Act IV behavior)
                */

                // Pre-calculate terrain projected points for this frame to snap to
                const terrainProjected: { x: number, y: number, z: number, r: number, g: number, b: number }[] = new Array(terrain.length);

                // Only calc 3D if we are transitioning or in Act IV
                if (transT > 0) {
                    for (let i = 0; i < terrain.length; i++) {
                        const t = terrain[i];
                        // Animate terrain height (waves)
                        const waveHeight = t.y + Math.sin(t.x * 0.02 + time) * 50 + Math.cos(t.z * 0.02 + time * 0.5) * 50;

                        // Color Logic based on height and scanner
                        const distToScan = Math.abs(t.z - scannerZ);
                        let r = 80, g = 80, b = 90; // Base Grey/Blue

                        // Scanner Interaction
                        if (distToScan < 200) {
                            if (waveHeight > 60) { r = 239; g = 68; b = 68; } // Red Peak
                            else if (waveHeight < -60) { r = 212; g = 168; b = 83; } // Gold Valley
                            else { r = 150; g = 150; b = 255; } // Scanner normal
                        }

                        // 3D Projection Logic
                        // World to Camera
                        const x0 = t.x;
                        const y0 = waveHeight;
                        const z0 = t.z;

                        // Rotate Y
                        const x1 = x0 * Math.cos(rotY) - z0 * Math.sin(rotY);
                        const z1 = x0 * Math.sin(rotY) + z0 * Math.cos(rotY);

                        // Rotate X (Tilt)
                        const y2 = y0 * Math.cos(rotX) - z1 * Math.sin(rotX);
                        const z2 = y0 * Math.sin(rotX) + z1 * Math.cos(rotX);

                        // Translate Cam
                        const z3 = z2 - camZ; // Move scene relative to cam

                        // Project
                        if (z3 > 10) {
                            const scale = fieldOfView / z3;
                            terrainProjected[i] = {
                                x: cx + x1 * scale,
                                y: h / 2 - camY * scale / 4 + y2 * scale, // Adjust vertical pos
                                z: z3,
                                r, g, b
                            };
                        } else {
                            terrainProjected[i] = { x: -9999, y: -9999, z: -9999, r, g, b };
                        }
                    }
                }


                ctx.lineWidth = 1;

                particles.forEach((p, i) => {
                    // ACT III TARGET
                    const textEase = Math.max(0, Math.min(1, (a3Entry - 0.15) * 3));
                    const noiseX = Math.sin(time + p.y * 0.05) * 20 * (1 - textEase);
                    const noiseY = Math.cos(time + p.x * 0.05) * 20 * (1 - textEase);
                    const tx = p.tx + noiseX;
                    const ty = p.ty + noiseY;

                    // ACT IV TARGET 
                    let targetX = tx;
                    let targetY = ty;
                    let color = `rgba(212, 168, 83, ${a3Opacity})`; // Default Gold Text

                    // If transitioning to Terrain
                    if (transT > 0 && p.targetGridIndex !== undefined && terrainProjected[p.targetGridIndex]) {
                        const tp = terrainProjected[p.targetGridIndex];
                        if (tp.z > 0) { // If visible
                            // Explosion effect: Add random scatter based on 1-transT (middle of transition)
                            // Actually, let's just lerp cleanly but add some noise during transition
                            const scatter = Math.sin(transT * Math.PI) * 100; // Bulge out during morph
                            const sx = (Math.random() - 0.5) * scatter;
                            const sy = (Math.random() - 0.5) * scatter;

                            // LERP
                            targetX = tx * (1 - transT) + tp.x * transT + sx;
                            targetY = ty * (1 - transT) + tp.y * transT + sy;

                            // Color shift
                            // Text is Gold. Terrain is calculated RGB.
                            const tr = tp.r;
                            const tg = tp.g;
                            const tb = tp.b;

                            // Simple blend could be hard, let's switch based on dominance
                            if (transT > 0.8) {
                                color = `rgba(${tr}, ${tg}, ${tb}, ${a4Opacity})`;
                            } else {
                                color = `rgba(212, 168, 83, ${a3Opacity})`;
                            }
                        }
                    }

                    // DRAW
                    if (a3Opacity > 0 || a4Opacity > 0) {
                        // Move particle towards target
                        p.x += (targetX - p.x) * 0.1;
                        p.y += (targetY - p.y) * 0.1;

                        ctx.fillStyle = color;
                        const size = (transT > 0.5) ? 2.5 : 1.5; // Bigger dots for terrain nodes
                        ctx.fillRect(p.x, p.y, size, size);
                    }
                });

                // Draw Grid Connections (Only in Act IV dominance)
                if (transT > 0.8) {
                    ctx.strokeStyle = `rgba(100, 100, 100, ${a4Opacity * 0.2})`;
                    ctx.lineWidth = 1;

                    // Connect points that are effectively projected
                    // We can't use the simple loop easily because points are scattered in particle array
                    // Use the 'terrainProjected' array directly for lines

                    // Rows
                    for (let r = 0; r < terrainRows; r++) {
                        ctx.beginPath();
                        let drawing = false;
                        for (let c = 0; c < terrainCols; c++) {
                            const idx = r * terrainCols + c;
                            const pt = terrainProjected[idx];
                            if (pt && pt.z > 0) {
                                if (!drawing) { ctx.moveTo(pt.x, pt.y); drawing = true; }
                                else { ctx.lineTo(pt.x, pt.y); }
                            } else {
                                drawing = false;
                            }
                        }
                        ctx.stroke();
                    }
                    // Cols
                    for (let c = 0; c < terrainCols; c++) {
                        ctx.beginPath();
                        let drawing = false;
                        for (let r = 0; r < terrainRows; r++) {
                            const idx = r * terrainCols + c;
                            const pt = terrainProjected[idx];
                            if (pt && pt.z > 0) {
                                if (!drawing) { ctx.moveTo(pt.x, pt.y); drawing = true; }
                                else { ctx.lineTo(pt.x, pt.y); }
                            } else {
                                drawing = false;
                            }
                        }
                        ctx.stroke();
                    }
                }
            }

            animationFrameId = requestAnimationFrame(render);
        };
        render();

        return () => {
            window.removeEventListener("resize", resize);
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return <canvas ref={canvasRef} className="block w-full h-full" />;
}
