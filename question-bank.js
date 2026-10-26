/* =====================================================================
   SCOREFREE QUESTION BANK  (Clerk Mains: IBPS and SBI)
   ---------------------------------------------------------------------
   Every test (1 to 10) of every subject already exists and opens with
   the official number of question slots, timer and marking scheme.
   Slots with no question show "being prepared" and are not scored.

   HOW TO ADD QUESTIONS
   1. Find the right line at the bottom of this file, or copy a line.
   2. Write:  SF_BANK.exam.subject[testNumber] = [ question, question, ... ];
        exam     = ibps  or  sbi
        subject  = reasoning, quant, english, awareness
        test     = 1 to 10
   3. Each question looks like this (comma after every question):

      {
        topic: "Syllogism",                 // shown above the question
        q: "Question text goes here?",
        opts: ["Option A", "Option B", "Option C", "Option D", "Option E"],
        ans: 2,                             // correct option: 0=A, 1=B, 2=C, 3=D, 4=E
        exp: "Short explanation shown after submit."
      },

   For a puzzle / data set, add these two lines to EVERY question of the set:
        setTitle: "Puzzle Set 1 - Seating arrangement",
        setIntro: "Eight friends sit in a row...",

   Questions run in the order you list them. Official counts:
     IBPS: reasoning 40, quant 35, english 40, awareness 40
     SBI : reasoning 50, quant 50, english 40, awareness 50
   Fewer questions is fine; the rest stay as "being prepared" slots.

   SAFETY TIP: after editing, open the site. If a test window does not
   open, you most likely forgot a comma or a quote mark in this file.
   ===================================================================== */
window.SF_BANK = { ibps: {}, sbi: {} };
['ibps', 'sbi'].forEach(function (e) {
  ['reasoning', 'quant', 'english', 'awareness'].forEach(function (s) {
    SF_BANK[e][s] = {};
    for (var t = 1; t <= 10; t++) SF_BANK[e][s][t] = [];
  });
});

/* ---------- ADD YOUR QUESTIONS BELOW THIS LINE ---------- */

// Example (remove the two slashes at the start of each line to use it):
// SF_BANK.ibps.quant[2] = [
//   { topic: "Percentage", q: "What is 20% of 250?", opts: ["30","40","50","60","70"], ans: 2, exp: "20/100 x 250 = 50." },
//   { topic: "Ratio", q: "Divide 90 in the ratio 2:3.", opts: ["30:60","36:54","40:50","45:45","20:70"], ans: 1, exp: "2/5 x 90 = 36 and 3/5 x 90 = 54." }
// ];
