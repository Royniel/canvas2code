import React from 'react';

const PaymentDetail = () => {
  return (
    <div className="min-h-screen bg-gray-100 font-sans antialiased text-gray-800">
      {/* Top Status Bar and Header Section */}
      <div className="bg-white pb-4 shadow-sm">
        {/* Top Status Bar */}
        <div className="flex justify-between items-center px-4 py-2 text-sm">
          <div className="font-bold">4:08</div>
          <div className="flex items-center space-x-1.5 text-gray-500">
            {/* Signal - simplified with 4 bars */}
            <div className="flex space-x-0.5 items-end h-3.5">
              <span className="w-1 h-1.5 bg-gray-500 rounded-[0.5px]"></span>
              <span className="w-1 h-2 bg-gray-500 rounded-[0.5px]"></span>
              <span className="w-1 h-2.5 bg-gray-500 rounded-[0.5px]"></span>
              <span className="w-1 h-3 bg-gray-300 rounded-[0.5px]"></span> {/* Last bar lighter */}
            </div>
            {/* Wifi Icon */}
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.288 15.038a5.5 5.5 0 017.424 0M5.475 12.176a9 9 0 0113.049 0m-2.924 2.923a2.5 2.5 0 01-3.6 0M12 17.5V18" />
            </svg>
            {/* Battery Icon */}
            <div className="relative w-7 h-4 border border-gray-400 rounded-[3px] flex items-center justify-center">
              {/* Fill for 23% */}
              <div className="absolute left-[1.5px] top-[1.5px] w-[5.5px] h-[10px] bg-gray-700 rounded-[1px]"></div>
              {/* Battery percentage text */}
              <span className="text-[10px] font-medium text-white relative z-10 -top-[0.5px]">23</span>
              {/* Battery "nub" on the right */}
              <div className="absolute right-[-2.5px] top-1 w-[2px] h-2 bg-gray-400 rounded-r-[1px]"></div>
            </div>
          </div>
        </div>

        {/* Header with Back Button and Title */}
        <div className="flex flex-col items-center pt-2">
          <div className="flex items-center justify-center w-full relative mb-1">
            <button className="absolute left-4 text-gray-800">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path></svg>
            </button>
            <h1 className="text-lg font-semibold">Payment</h1>
          </div>
          <p className="text-gray-500 text-sm">April 04, 2026, 9:51 PM</p>
        </div>
      </div>

      {/* Main Payment Card */}
      <div className="bg-white mx-4 mt-4 p-5 rounded-xl shadow-sm text-center">
        <p className="text-base font-medium text-gray-900 mb-2">Kristy Carabello</p>
        <p className="text-5xl font-bold text-gray-900 mb-2 leading-none">+$1,769.44</p>
        <p className="text-gray-600 text-sm italic mb-6">"Vertige / March. Thank you!"</p>
        <button className="text-blue-600 border border-blue-600 rounded-full px-5 py-2 text-sm font-medium hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50">
          More details
        </button>
      </div>

      {/* Pay or Request Button */}
      <div className="px-4 mt-8">
        <button className="w-full bg-blue-600 text-white font-semibold py-4 rounded-full text-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors">
          Pay or request
        </button>
      </div>

      {/* Likes and Comments Card */}
      <div className="bg-white mx-4 mt-8 p-5 rounded-xl shadow-sm">
        <h2 className="text-gray-900 text-base font-medium mb-3">Likes and Comments</h2>
        <div className="flex space-x-6 text-gray-600">
          <div className="flex items-center space-x-1">
            {/* Heart Icon */}
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 22l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>
            <span>0</span>
          </div>
          <div className="flex items-center space-x-1">
            {/* Chat Bubble Icon */}
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
            <span>0</span>
          </div>
        </div>
      </div>

      {/* Status and Transaction Details Card */}
      <div className="bg-white mx-4 mt-4 p-5 rounded-xl shadow-sm mb-8">
        <h2 className="text-gray-900 text-base font-medium mb-3">Status</h2>
        <p className="text-gray-900 font-bold mb-4">Complete</p>

        <h2 className="text-gray-900 text-base font-medium mb-3">Transaction details</h2>
        <div className="flex items-center text-gray-600">
          <p className="text-sm mr-2">April 04, 2026, 9:51 PM</p>
          {/* Lock Icon */}
          <svg className="w-4 h-4 text-blue-600 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v3h8z"></path></svg>
          <span className="text-blue-600 text-sm font-medium">Private</span>
        </div>
      </div>
    </div>
  );
};

export default PaymentDetail;