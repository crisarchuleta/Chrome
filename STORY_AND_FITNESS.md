# Neon Coast: Body, Food and Story design

This is the plan for the fitness system, food, and the story with its characters. Everything here is original to
Neon Coast. Characters are friends and business partners only; there are no romances.

---

## 1. Your body

Each player has three body stats, saved between sessions:

| Stat | Range | Goes up from | Goes down from |
|---|---|---|---|
| **Strength** | 0–100 | Gym lifts, the punching bag, pull-ups, carrying heavy loads in missions, climbing | Slowly, if you never train |
| **Stamina** | 0–100 | Sprinting and jogging distance, swimming laps, treadmill, beach runs | Slowly, if you never train |
| **Body fat** | 8–40 % | Eating more than you burn (junk food and soda are the fastest way) | Burning more than you eat: activity, workouts, sprinting, swimming |

There's also **Energy** (0–100): how fuelled you are right now. Activity drains it and food refills it. Training
on low energy gains less, and you can't train when it's empty.

### Calories, honestly simplified
- One game day is 24 real minutes. Your body burns a base amount over a day, plus whatever your activity burns:
  sprinting, swimming, climbing and workouts burn the most.
- Whatever you eat beyond that becomes fat, slowly; a deficit burns it off, slowly. One big burger meal won't
  change you, but a week of three-burger days will.
- Workouts build muscle best when you're fed. A protein shake after training adds a strength bonus.

### What your body does

| | Weak and skinny | Average | Athletic | Muscular | Heavy |
|---|---|---|---|---|---|
| How you get there | Cardio only, no lifting, little food | Do nothing in particular | Lots of cardio, some lifting, eat right | Lots of lifting, eat enough | Lots of junk food, little activity |
| Sprint speed | normal | normal | +6 % | +2 % | down to −18 % |
| Sprint time | long | 12 s | up to 24 s | 14 s | down to 7 s |
| Climb and vault | slower, can't hang long | normal | quick | quick, strong pull-ups | slow; the highest walls are out of reach |
| Jump | normal | normal | normal | normal | lower |
| Fall damage | normal | normal | normal | a bit less | more |
| Carry heavy items (missions) | no | light only | medium | heavy | medium |
| Punch / shove | weak | normal | normal | strong | strong ("not so much weak") |
| Looks | narrow frame | average | lean, slightly broad | broad shoulders and chest | wider, deeper body |

- **Looks:** your body shape changes for everyone to see. It uses the Humanoid's width and depth scale today, and
  will use MakeHuman body variants (skinny, average, heavy, muscular) once those are in the game.
- **Builds:** fat and muscle are separate numbers, so they combine. You can be strong and heavy (powerful but
  slow) or skinny and fit (fast and tireless, but can't lift the safe).

### Where you train
- **Iron Tide Gym on the beach (Dante's).** Bench press, squat rack, pull-up bar, dumbbells, punching bag,
  treadmill.
- **Muscle Beach outdoor gym.** Free, with fewer machines.
- **A home gym** in your house, once you buy the equipment.
- **Real activity counts too:** running anywhere, swimming in pools and the ocean, climbing.
- **Workouts are short rhythm mini-games:** press in time to keep good form. Good form gains more, sloppy form
  gains less. Everyone sees you lifting.

### Food
- **Fast food:** Taco stand, pizza place, burger joint, cafe pastries, food trucks.
- **Vending machines:** soda and candy, cheap, lots of calories.
- **Healthy:** Sol's food truck (once you unlock her healthy menu), smoothie bar, salad place.
- **Food menu** (calories, energy, extra effect):

  | Food | Price | Calories | Energy | Extra |
  |---|---|---|---|---|
  | Soda | $5 | 250 | +10 | a sugar rush, then a crash |
  | Candy bar | $4 | 280 | +12 | |
  | Fries | $8 | 400 | +15 | |
  | Burger | $14 | 900 | +35 | |
  | Pizza slice | $6 | 300 | +12 | |
  | Tacos (3) | $12 | 600 | +30 | |
  | Energy drink | $9 | 150 | +25 | |
  | Salad | $11 | 250 | +20 | |
  | Smoothie | $10 | 300 | +25 | |
  | Protein shake | $12 | 200 | +15 | boosts your next workout |

- Eating plays a short eating pose (everyone sees it) and gives a little health back.
- **The phone's Body app** shows your stats, your build, today's calories in and out, and a coach tip from Dante.

---

## 2. The story: "Neon Coast"

### The setup
You step off the bus in Neon Coast with $250 and a phone. The city is sun, neon and money. A developer named
**Calder Voss** is buying up the whole coastline, block by block, and the small businesses that make the city
what it is are being squeezed out. You fall in with the people trying to hold on, and help them turn their
businesses into an empire of their own.

### Your crew (friends and business partners)

- **Marisol "Sol" Vega**, food truck chef.
  - Personality: warm and fast-talking, and she knows everyone.
  - Story role: your first friend in town and your first business partner.
  - Gameplay: food deliveries and catering. She unlocks the healthy menu, and later a restaurant you co-own.
- **Dante Okafor**, ex-boxer who owns the Iron Tide Gym.
  - Personality: calm, blunt and loyal.
  - Story role: your trainer and your crew's muscle. Voss wants his gym's beach lot.
  - Gameplay: strength and stamina challenges, sparring, beach races, the parkour course.
- **Wren Takahashi**, phone and network genius.
  - Personality: sarcastic, and never leaves her apartment.
  - Story role: she built your phone. She's the eyes and ears of every job.
  - Gameplay: phone missions, tailing, signal-tower climbs (climbing), the skyscraper job.
- **Frank "Uncle Frank" Delacroix**, Palmgrove mechanic and fixer.
  - Personality: old-school and full of stories.
  - Story role: the getaway driver mentor. His garage is your base.
  - Gameplay: car missions, street races, and police escapes (the Coast Patrol).
- **Priya Raman**, property broker.
  - Personality: sharp, and always on two phones.
  - Story role: the legitimate money. She shows you how Voss is really doing it.
  - Gameplay: buying properties (homes), business fronts, and the endgame plan.

### The other side
- **Calder Voss:** the smiling developer behind Voss Horizon, the glass tower downtown.
- **"Rook" Mendez:** Voss's fixer, who does the threats.
- **Captain Harlan Price:** a Coast Patrol captain on Voss's payroll.

### Chapters

1. **Fresh Off the Bus.** Meet Sol at her food truck.
   - Deliver tacos on foot (learn to sprint and manage stamina), eat your first meal, and run into Dante.
   - Fitness tutorial: your first workout at Iron Tide.
   - *Unlocks: the Body app, food, the gym.*
2. **Iron Tide.** Rook's crew trashes the gym and steals Dante's equipment.
   - Chase a thief across rooftops (vault, climb, Stamina 25 recommended).
   - Carry the stolen weights back (needs Strength 20, or two trips if you're weaker).
   - Win the beach race Dante sets up to raise money.
   - *Unlocks: the Muscle Beach gym and Dante's challenges.*
3. **Signal.** Wren wants into Voss's network.
   - Climb three signal towers to plant relays (climbing; heavy bodies can't reach the top).
   - Tail Rook through downtown without being seen.
   - Ride the office tower elevator (or take the stairs) to plant the last relay on the roof, then BASE-jump off
     with a parachute to lose the guards.
   - *Unlocks: Wren's phone jobs.*
4. **Wheels.** Frank teaches you to drive like a pro.
   - Street race through Palmgrove.
   - Steal back Sol's impounded truck from the Coast Patrol lot (escape a 2-star chase).
   - Captain Price is exposed as being on Voss's payroll.
   - *Unlocks: Frank's races and the garage base.*
5. **Coastline.** Priya shows how Voss buys the coast with fake permits.
   - Buy your first property to block a Voss deal.
   - Collect proof: break into the Voss Horizon tower records room. You can go in quietly (stamina and climbing)
     or go in loud.
   - The finale: crash Voss's launch party on the tower roof and broadcast the proof across the city, then
     escape any way you like (parachute, elevator, stairs, car).
   - *Ending: the crew's businesses are safe, and you're partners in all of them.*

### Side jobs, endless and fitness-linked
- **Dante's challenges:**
  - Bench press for reps (Strength).
  - Beach runs against the clock (Stamina).
  - Pull-up ladder.
  - The parkour course across the downtown rooftops.
  - Rewards: cash and stat boosts.
- **Sol's catering runs:** deliver hot food on time, on foot or by car. Heavy orders need strength or a car.
- **Wren's tower climbs:** reach the top of radio and billboard towers, scan, and parachute down.
- **Frank's street races and stunt jumps.**
- **Priya's property flips:** buy, fix up (carry materials), sell.
- **Lifeguard shifts at the beach:** swim out to people in trouble before time runs out (Stamina makes you
  faster).
- **Food Critic:** eat at every restaurant in the city. It's fun, but your body will show it.

### How the story runs in the game
- **Story contacts:** Sol, Dante, Wren, Frank and Priya stand at their places around the city, with a marker
  above their heads when they have a job for you. Your phone lists them, so you can call for side jobs.
- **Missions are data:** a list of steps such as talk, go to, follow, chase, collect, carry, climb, workout, eat,
  deliver, survive wanted, and reach. A MissionService runs them, with objective markers, a dialogue box and
  rewards.
- **Progress is saved:** the chapter you're on, missions done, contacts met.
- **Everyone sees it:** the contacts and their animations are visible to all players. Missions are personal, but
  two players can join the same job.
