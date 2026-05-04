import React from 'react';

const SouthIndianChart = () => {
    const chartSize = 500; // Fixed width and height for the chart in pixels
    const borderWidth = 3; // Thickness of the chart lines
    const lineColor = '#c09a5b'; // Gold-brown color for lines and borders
    const bgColor = '#fdfaf1'; // Light cream background color

    // Calculate the length of the main diagonals for a square of `chartSize`
    const mainDiagonalLength = Math.sqrt(chartSize * chartSize * 2);

    // Data for all celestial body and sign number placements
    // Each object defines content, its Tailwind CSS color class, font size, and
    // top/left percentages for absolute positioning within the chart container.
    const placements = [
        // House (Top-center rhombus)
        { content: 'Su', color: 'text-orange-400', top: '10%', left: '46%', fontSize: 'text-sm font-semibold' },
        { content: 'Mo', color: 'text-indigo-400', top: '14%', left: '46%', fontSize: 'text-sm font-semibold' },
        { content: '1', color: 'text-violet-800', top: '7%', left: '60%', fontSize: 'text-xs font-bold' },
        { content: '12', color: 'text-violet-800', top: '7%', left: '30%', fontSize: 'text-xs font-bold' },

        // House (Right-center rhombus)
        { content: 'Ne', color: 'text-teal-500', top: '48%', left: '76%', fontSize: 'text-sm font-semibold' },
        { content: '1', color: 'text-violet-800', top: '30%', left: '88%', fontSize: 'text-xs font-bold' },
        { content: '9', color: 'text-violet-800', top: '60%', left: '88%', fontSize: 'text-xs font-bold' },

        // House (Bottom-center rhombus) - Only sign numbers present
        { content: '10', color: 'text-violet-800', top: '90%', left: '60%', fontSize: 'text-xs font-bold' },
        { content: '9', color: 'text-violet-800', top: '90%', left: '30%', fontSize: 'text-xs font-bold' },

        // House (Left-center rhombus)
        { content: 'Pl', color: 'text-purple-800', top: '48%', left: '10%', fontSize: 'text-sm font-semibold' },
        { content: '6', color: 'text-violet-800', top: '60%', left: '7%', fontSize: 'text-xs font-bold' },
        { content: '7', color: 'text-violet-800', top: '30%', left: '7%', fontSize: 'text-xs font-bold' },

        // House (Top-left triangle)
        { content: '3', color: 'text-violet-800', top: '7%', left: '7%', fontSize: 'text-xs font-bold' },
        { content: '4', color: 'text-violet-800', top: '17%', left: '7%', fontSize: 'text-xs font-bold' },

        // House (Bottom-left triangle)
        { content: '6', color: 'text-violet-800', top: '80%', left: '7%', fontSize: 'text-xs font-bold' },
        { content: '7', color: 'text-violet-800', top: '90%', left: '7%', fontSize: 'text-xs font-bold' },

        // House (Top-right triangle)
        { content: '12', color: 'text-violet-800', top: '17%', left: '88%', fontSize: 'text-xs font-bold' },
        { content: '1', color: 'text-violet-800', top: '7%', left: '88%', fontSize: 'text-xs font-bold' },

        // House (Bottom-right triangle)
        { content: '9', color: 'text-violet-800', top: '80%', left: '88%', fontSize: 'text-xs font-bold' },
        { content: '10', color: 'text-violet-800', top: '90%', left: '88%', fontSize: 'text-xs font-bold' },

        // House (Central Rhombus)
        { content: 'Ve', color: 'text-fuchsia-500', top: '38%', left: '46%', fontSize: 'text-sm font-semibold' },
        { content: 'Ju®', color: 'text-orange-500', top: '42%', left: '46%', fontSize: 'text-sm font-semibold' },
        { content: 'Sa®', color: 'text-slate-500', top: '46%', left: '46%', fontSize: 'text-sm font-semibold' },
        { content: 'Ra®', color: 'text-blue-500', top: '50%', left: '46%', fontSize: 'text-sm font-semibold' },
        { content: 'Ur', color: 'text-purple-500', top: '54%', left: '46%', fontSize: 'text-sm font-semibold' },
        { content: 'A2c', color: 'text-violet-800', top: '58%', left: '46%', fontSize: 'text-sm font-bold' }, // A2c (Ascendant) is typically bold
        { content: '5', color: 'text-violet-800', top: '30%', left: '30%', fontSize: 'text-xs font-bold' }, // Sign 5 (top-left of rhombus)
        { content: '11', color: 'text-violet-800', top: '30%', left: '60%', fontSize: 'text-xs font-bold' }, // Sign 11 (top-right of rhombus)
        { content: '8', color: 'text-violet-800', top: '70%', left: '45%', fontSize: 'text-xs font-bold' }, // Sign 8 (bottom of rhombus)

        // House (Mid-left quadrilateral, between Central and Left-Center)
        { content: 'Me', color: 'text-emerald-500', top: '70%', left: '26%', fontSize: 'text-sm font-semibold' },
        { content: 'Ma', color: 'text-red-600', top: '74%', left: '26%', fontSize: 'text-sm font-semibold' },
        { content: 'Ke®', color: 'text-amber-800', top: '78%', left: '26%', fontSize: 'text-sm font-semibold' },
    ];

    return (
        <div
            className="relative border-[3px] border-[#c09a5b] select-none"
            style={{
                width: `${chartSize}px`,
                height: `${chartSize}px`,
                backgroundColor: bgColor,
                boxSizing: 'content-box', // Ensure border doesn't add to the total width/height
                fontFamily: 'sans-serif', // Modern, professional default font
            }}
        >
            {/* Corner circles (small decorative rings at the outer corners) */}
            <div className="absolute w-4 h-4 rounded-full border-[2px] border-[#c09a5b] -top-2 -left-2 bg-transparent"></div>
            <div className="absolute w-4 h-4 rounded-full border-[2px] border-[#c09a5b] -top-2 -right-2 bg-transparent"></div>
            <div className="absolute w-4 h-4 rounded-full border-[2px] border-[#c09a5b] -bottom-2 -left-2 bg-transparent"></div>
            <div className="absolute w-4 h-4 rounded-full border-[2px] border-[#c09a5b] -bottom-2 -right-2 bg-transparent"></div>

            {/* Inner rotated square (diamond shape) which forms the central grid structure */}
            <div
                className="absolute bg-transparent border-[3px] border-[#c09a5b]"
                style={{
                    width: `${chartSize * Math.SQRT1_2}px`, // Side length of a square rotated 45 degrees
                    height: `${chartSize * Math.SQRT1_2}px`,
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%) rotate(45deg)',
                }}
            ></div>

            {/* Main diagonal lines (connecting outer corners of the chart) */}
            <div
                className="absolute bg-[#c09a5b]"
                style={{
                    width: `${mainDiagonalLength}px`,
                    height: `${borderWidth}px`,
                    top: '50%',
                    left: '50%',
                    transform: `translate(-50%, -50%) rotate(45deg)`,
                }}
            ></div>
            <div
                className="absolute bg-[#c09a5b]"
                style={{
                    width: `${mainDiagonalLength}px`,
                    height: `${borderWidth}px`,
                    top: '50%',
                    left: '50%',
                    transform: `translate(-50%, -50%) rotate(-45deg)`,
                }}
            ></div>

            {/* Watermark: `astrotalk.com` repeated across the background */}
            {Array.from({ length: 4 }).map((_, i) => (
                Array.from({ length: 4 }).map((_, j) => (
                    <div
                        key={`wm-${i}-${j}`}
                        className="absolute text-gray-300 font-bold opacity-10 pointer-events-none text-2xl"
                        style={{
                            top: `${(i * 33) + 15}%`, // Spacing for rows
                            left: `${(j * 33) + 15}%`, // Spacing for columns
                            transform: `translate(-50%, -50%) rotate(-45deg)`, // Rotate and center
                            whiteSpace: 'nowrap', // Prevent text from wrapping
                        }}
                    >
                        astrotalk.com
                    </div>
                ))
            ))}

            {/* Render all planet and sign number placements based on the `placements` data */}
            {placements.map((p, index) => (
                <div
                    key={index}
                    className={`absolute ${p.color} ${p.fontSize} leading-none`}
                    style={{ top: p.top, left: p.left, transform: 'translate(-50%, -50%)' }} // Center text using translate
                >
                    {p.content}
                </div>
            ))}

            {/* Copyright text at the bottom right corner */}
            <div className="absolute bottom-1 right-2 text-[8px] text-gray-500 font-medium">
                ©astrotalk.com
            </div>
        </div>
    );
};

export default SouthIndianChart;