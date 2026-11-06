# HW 5 — AI Prompts Log

A log of the prompts I typed into the vibe coder (Claude Code) for each problem in HW 5: Campus Customs Multi-Agent Operations.
Each problem is described in my own words; no assignment pages or URLs were pasted.
Each section has the problem number and title, my first prompt, any follow-up prompts, and one sentence on what the first prompt was missing.

---

## Problem 1: Vibe coder prompts

**Prompts:**

1. > ok broheem, i need to do HW 5. will you get me set up?

**Follow-up prompts:**

_What was lacking after the first prompt:_ The first prompt didn't give the assignment or data, so the follow-ups had to supply the HW 5 title, the database, and how we'd work through the problems.

2. > Id like to set this session up remote. coolio?
3. > Ok this one is called Homework 5: Campus Customs Multi-Agent Operations. Ready?
4. > Can you grab the data.zip  from my downloads folder and move it to HW5?
5. > Yes
6. > Ok. Well go through it one prompt at a time. I won't paste the whole scenario. If we need more information along the way I'll pull it from the scenario.
7. > Problem 1: Vibe coder prompts. Create AI_prompts.mb and keep it updated as we work. As usual, this file is the log of what I type to you. I will discribe each problem in my own words. This should be like we've done before. Each problem gets a section which includes:
   > The problem number and title
   > At least one prompt I have typed in my own words (as much as possible)which occasionally get a little groovy.
   > One follow-up prompt if needed with a on what was lacking after the first prompt
8. > Okay, bro. I did not give you the scenario previously because I thought it would come through in the prompts, but there's stuff in here that I think we need to consider that I'm not seeing in the prompts on a first pass. So I'm going to give you the scenario and some data information and then the rules for the shop, and we will integrate it into the work that we're doing for this homework. Sound good?
9. > Cool. This is the scenario. Canvas Customs multi-agent operations is an agentic team that runs a online shop. open tickets, go to a board, customer orders, rent, unpaid bills, discount requests, whatever the shop has to handle. We're building three pieces that talk to each other, an MCP server, a fast API backend with multi-agent team, and a React dashboard so a human can watch the agents at work and approve the requests. Our agent team should have full connectivity. Any agent may delegate tasks to any other agent for help. In this assignment, we will build these agents. There will be a boss agent that reads each ticket and decides who should work on it and makes the final calls. We will also have an inventory agent It checks stock by SKU and size, spots shortfalls, and figures out which vendor can restock. We're going to have an accounting agent, watches cash and invoices, checks margins, and prepares payments or purchase orders for human approval. We'll also have a facilities agent, handles the shop space side, leases, rent, etc. Finally, we'll have a customer service agent that drafts messages for customers. Let's verify we've got the scenario set up, and then I'll give you some data information. Got it?
10. > Okay, before we go to data, I want to  I want to let you know that we still have problems 5 through 11 to work. So let's not go crazy and try and meet all the scenario set up yet. Let's work through the problems, and if we find we've missed something, let's fix it then. Does that work for you?
11. > All right, we've got data section. And we're going to download a zip file and unzip it so that we have the data campus underscore customs dot db, which we've done. In that file, we have the shop database. The tables include desk, tickets, inventory, pricing, vendors, leases, cash accounts, payments, and invoices. Our tools will update the database as tickets get resolved. We need to make a copy of the database file called data/campus_customs_new.db. I believe we have done this already as well. our MCP server and backend will point to the working copy of campus customs database we created. We'll keep the campus _customs.db untouched so that we can reset the new database at our leisure. You dig?
12. > Alright, man. We got rules of the shop. The field desk.date underscore today is quote today for the shop. And we'll use this date to determine what is overdue. Our vendor lead times come from the vendors table. A vendor will not ship a new product while they still have an open unpaid invoice. Human approval is required for any payments. Points will be deducted for if this is not done. So let's make sure we do that, okay? If a payment is made, make sure to update the relevant table. There's not enough cash. The pay tool must refuse. We can't have a negative balance. Cash only goes out in this homework. We did not model revenue, so no money comes in. Before a full run to resolve the tickets, make sure to reset the database to the original values. This is very important. Do not email customers or call real vendors. Should say so on the board, but I want to make sure that that is well understood before we move forward. Finally, we'll use the port key underscore API underscore key for API calls. I believe that's in my root directory. We also need to make sure that this is protected and not published to the GitHub or any other places where this key might be found and used by anyone other than me. For this assignment, use only GPT-6-Luna, through the port key for every agent. The multi-agent chats can burn tokens fast, and points will be deducted if any model other than Luna shows up. In the code or runs by an agent or at all in this homework. We're supposed to work one problem at a time, as I discussed with you before, and I need to provide you each one in my own words, not paste the URL, not screenshot the problems to finish everything. Our final submission will be a public GitHub repo, and the last problem will show me the file tree. Are you good with all that background, and can you incorporate any of the safeguards that we identified that may need to be incorporated?

---

## Problem 2: Study the Campus Customs database

**Prompts:**

1. > Problem 2: Study the Campus Customs database
   > Open data/campus_customs.db, look through every table and it's fields. Find some way to present it to me here for review. Make a copy of data/campus_customs.db since later problems will update the working copy. Show me how the 3 open tickets link to other tables.
   > Start output/harness.md. For each table we need to list the fields and write a short line on why that table matters to our agents. This file will grow in later problems, precious.

_What was lacking after the first prompt:_ Nothing needed a follow-up. The prompt covered studying the tables, making the working copy, and starting harness.md in one go.

---

## Problem 3: Build the MCP server

**Prompts:**

1. > On brother. Problem 3: Build the MCP server
   > We need to write an MCPserver in mcp_server/ using FastMCP. This is going to talk to campus_customs_new.db. We are not connecting or running it in this problem.
   > "Every agent in this homework uses the tools in this MCP server." We need three tools we will need for the tickets in the database at this time. We will add more tools later. "Keep the names clear. Never invent data, only use information in the database."
   > In output/harness.md list the each of our 3 MCP tools. Each tool needs the following:
   > Which table it reads
   > Which ticket it helps unlock (101, 102, or 103)
   > One sentence describing why that is the right tool for that ticket
   > Also, we need a short mcp_server/README.md which explains what the MCP server is for, which database file it uses, and the tools it has.

_What was lacking after the first prompt:_ Nothing needed a follow-up. The prompt named the folder, the database, the three-tool limit, the harness fields, and the README, so the server was built from it directly.

---

## Problem 4: Add MCP server to Vibe Coder and test each tool

**Prompts:**

1. > Problem 4, add MCP server to Vibe Coder and test each tool
   > I need you to add the MCP server to this project so we can call the tools. We need to save the connection JSON text in .mcp.json at the project root.
   > Next, we're going to test each of the tools and save evidence in output/mcp_smoke.json. For each tool, we need to include the prompt I asked you, the tool name, the tool output. It must match the values in data/campus_customs_new.db.

**Follow-up prompts:**

2. > Paused go.
3. > Done, reloaded
4. > Add to course .mcp.json

5. > I need a bulldog tee in size S. what you got for me?
   > I need the rent due and due date for lease 1.
   > can you hook me up with the cost and list price of the navy hoodie? super fly.

_What was lacking after the first prompt:_ The first prompt didn't account for this session being rooted in the course folder, so the server also had to be registered in the course-level .mcp.json before Claude Code would load it.

---

## Problem 5: Build the agent team and grow the MCP tools

**Prompts:**

1. > All right, man, we've got problem 5. Build the agent team and grow the MCP tools. We'll start by building the agentic team for the campus customs. We'll use pedantic AI. As we've discussed before, we've got a boss, inventory, accounting, facilities, and customer service agents. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. I believe we discussed this previously. We're going to put the agent prompts in backend / prompts / with one file per agent. Put data types in backend / models.py and the agent files under backend / he wanted to make sure we knew that our layout can vary some as long as the 5 roles are clear. We're going to use our port key and only GPT-6-Luna, again, as previously discussed. We're going to write each prompt in my words with the shop rules that the agent needs. Again, I've given you those rules, so I think we're ready. More detailed prompts that cover all aspects of an agent work and scope score higher than short generic prompt. So let me know if you think I need to embellish my prompts some. Next, we're going to need to add any tools that the agent needs to my MCP server so they can work on the open tickets. The shop facts come from the MCP server over data / campus / customs / new .db. We're not going to invent a second shop tools layer that bypasses the MCP. We're going to wire these agents so that they append to output / audit / trail .json as they run. For each agent loop step, record enough of the enough to audit it later. We're going to append this file and not wipe it after each run. In our output / harness.md, we need to list each agent and each MCP tool, including the ones we add in this problem, along with the table the tool uses. Also, we need to add a short safety section. In the safety section, we need guardrails a real business would want when agents touch real customers and real money. So I'm going to ask you to come up with some of those for us. Plus, we need limits that keep token use in check. Finally, we'll update the MCP underscore server / readme.md so that the tool list matches what we've done. Do you have any questions about this, or are you ready to execute?

**Follow-up prompts:**

2. > Can you give me recommendations on agents prompts? I thought we addressed human approval requirements in the problems set up. Do you really need additional information? Lets not live test yet.
3. > You've been working with me a while. Put them in my voice and i will review, cool?
4. > Paused, go

_What was lacking after the first prompt:_ The first prompt didn't say who drafts the agent prompts or confirm how human approval should be enforced, so follow-ups settled that I'd draft them in my voice for review and that agents can only request payments.

---

## Problem 6: Plan the 3 tickets

**Prompts:**

1. > Okay, we're on to problem 6, plan the 3 tickets. Before we wire the back end, we're going to write down what we expect the team to do on each open ticket. We're going to build output slash desk underscore tickets dot html. A page we can double click with one tab per ticket, 101, 102, and 103. I'm also going to add empty cache and reflection tabs for later problems. Let's leave them blank with a shortcoming later note for now. On each ticket, fill an expected section only. Leave room for an actual section we will fill in after we run the agents. For each ticket's expected section, we need to write in my own words who the boss should call first and why. All the agent delegations we expect, not boss calls everyone, which MCP tools we expect that run to use. If we run every specialist on every ticket, we score low. We should compare the plan to what actually happens when the agents solve the three tickets. Can you show me what the tickets are again for my evaluation and help me generate a plan for each ticket?

**Follow-up prompts:**

2. > Build it

_What was lacking after the first prompt:_ The first prompt asked for help generating the plans, so a follow-up was needed to approve the drafted plans before the page was built.
3. > i think we inherited the black pink style from my prof. can we update to the 70s/80s rock/metal style we established in the previous hw?
4. > dude, i love it! could we turn it down low, and get like an art deco/big band vibe?  That goes together right?

---

## Problem 7: Backend routes

**Prompts:**

1. > So cool. Now we're on the problem 7, backend routes. Our React front-end dashboard, which we'll build in the next problem, needs a backend it can call. So we're going to go to backend/main.py. We're going to use fast ATP, and we're going to add routes that do the following: return 3 tickets and whether each is open or resolved, take a ticket ID and run our agent team on that ticket, return recent agent events, that is what each agent said and which tools they used. This is so that the board can be refreshed. We're going to approve a payment or purchase after a human clicks approve. Agent only prepares the pay. This route is what actually changes cash. We're going to return the current checking balance from cash accounts. And finally, we're going to reset the database to the original values when we want to try a fresh run. From backend folder, we'll start the server with a terminal call I'll post in. And this should return our backend at http://localhosts:8000. So the front end dashboard can call these routes. Then in our output/harness.md, list each route in one line, what URL, and what it does. wait for me to paste the terminal, and then we'll go.

**Follow-up prompts:**

2. > uvicorn main:app --reload --port 8000
3. > Paused, go

_What was lacking after the first prompt:_ The first prompt held back the start command, and it didn't cover listing or rejecting approvals, so I supplied the command and the board got approvals and reject routes too.

---

## Problem 8: Agent dashboard

**Prompts:**

1. > All right, bro, now we are going to build the front end dashboard in frontend/ with React  + Vite + TypeScript. This is problem 8, agent dashboard. The page should call the routes we built in problem 7. At minimum, the dashboard should include the following: list of all three tickets, let you pick one ticket and start the agent team on it, show each agent and what they are saying slash doing while the ticket runs, mark a ticket resolved when the run finishes, show short summary of what each agent did on the ticket, let a human approve and pay or purchase when asked, show the checking balance it should drop after an approved. Make the dashboard look good. Be creative with the layout or feel. This is a real desk people would want to sit at, so put thought into how it looks. I think we've done that, but take another look and make sure it follows those parameters. Runner needs to talk to the backend at http://localhost:8000. In the backend, allow the VIT page origin. This is usually going to be at http://localhost:5173. So the browser is allowed to call the routes. I've got another terminal to post to you to start the board. I will do that after this message. This opens up the React desk to our browser so we can pick tickets and watch the agents. Finally, we need to write output/design.md with what we choose for the dashboard look, layout, how agents read differently, how resolved tickets and cash show up, and why, including the creative choices that make it feel special and something humans would actually enjoy using. Any questions?

**Follow-up prompts:**

2. > npm run dev
3. > i really like our styling. what would you think about adding something between art deco and 70s counterculture? im thinking something with a midcentry modern vibe? i feel like we have associated music with each era/feel. maybe rockabilly?

_What was lacking after the first prompt:_ The first prompt held back the command to start the board, so the frontend had to be installed and started from a follow-up terminal command, and a 1956 rockabilly volume was added afterward.

---

## Problem 9: Resolve the tickets

**Prompts:**

1. > Okay, here we finally are. It's time to resolve those tickets. With problem 9, resolve the tickets. Before we test the agents on a full run over the 3 tickets, reset the working database from data slash campus underscore customs underscore new dot db. Again, so we start clean. Let's verify the starting checking balance. Then we'll run all 3 tickets on the board. 101, 102, 103, until each is resolved. Open output backslash desk underscore tickets dot html from problem 6. On each ticket tab, fill the actual section from this run, which agents worked, what they delegated, and which tools they used. Keep our expected section so we can compare the two. Now let's talk about the cache tab. Of the same output backslash desk underscore tickets dot html. Let's itemize the money in the following way. Start checking balance after the reset. For each ticket, how cash changed when the ticket resolved, and why, which pay slash purchase dollar amount. And we'll check the ending balance. It must match cash underscore accounts in the working database. So the wrong cash math loses points even if the board shows every ticket resolved. Also, we need to save output backslash resolve underscore tickets dot json for each ticket. We need ID, final status, short outcome, what each agent contributed, and any human approvals. Output backslash resolved underscore board dot html. Page you can double click with a screenshot of the React board for each resolved ticket. 101, 102, and 103. Finally, we need to append real runs to output backslash audit underscore trail dot json and finish output backslash harness.md so it covers tables, MCP tools, the 5 agents, API routes, the dashboard, and safety rules. You got all that?

**Follow-up prompts:**

2. > I'll click on board
3. > both are signed.
4. > Note it, resolve

_What was lacking after the first prompt:_ The first prompt didn't say who signs the payments or how a restock reorder should work. So I approved both payments on the board myself, and we decided reorders get recorded in the ticket note with no cash moving before the tickets could resolve.

---

## Problem 10: Reflection

**Prompts:**

1. > Alright, we are so close. Problem 10, reflection. Need to open an output desk underscore tickets.html and fill in the reflection tab. Need to answer in my vibe and be detailed and thorough. How would we evaluate performance of the agents on each ticket and why? For each ticket, how did actual compare to expected plan we wrote earlier? What would have been simpler as one agent with tools and why? Describe three new problems campus customs might face that this agent team could solve with the tools we've built. Finally, describe three new problems campus customs might face that this agent team could not solve with the tools we've built, and explain the tools and agents we would need to solve them. We need to tie every answer to this app and the three tickets we ran. Use the ticket tabs and cache tab on the same page as our evidence. Generic AI essays without campus customs details will score low. We, of course, want to score high. What do you think?

_What was lacking after the first prompt:_ Nothing needed a follow-up. The prompt said "cache tab", but it meant the Cash tab from Problem 9, so the reflection cites that tab.

## Problem 11: Submit to GitHub

**Prompts:**

1. > Ok here we are, Problem 11: Submit to GitHub
   > We need to push our code to a public GitHub repo so the grades can clone it. Then we will submit the repo URL to Canvas and also put it in output/github_url.txt.
   > Do not push my real .env to GitHub repo. Include both database files under data/ (the original and working copy) so graders can easily run the app.
   > The README should explain: copy original DB to the working copy when one needs a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB before a full three-ticket run.

_What was lacking after the first prompt:_ Nothing needed a follow-up. The prompt didn't name the repo, so we used `campus-customs-agents`, made `HW 5` its own repo so the rest of the course folder stays private, and left out `data.zip` because it holds the same original DB.
