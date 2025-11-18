#!/usr/bin/env python3
"""
Escape Across the Great Gobi — Fixed & Improved Version
Includes fixes for saving/loading, undefined attributes, and UI/logic clarity.
Usage: python gobi_escape_full_fixed.py
"""

import random
import json
import os
import time

SAVE_FILE = "gobi_escape_save.json"
TOTAL_DISTANCE = 200  # km to win
MAP_WIDTH = 40  # characters in ASCII progress bar

# ---------- Game Entities ----------

class Player:
    def __init__(self):
        self.thirst = 0            # 0-5 (5 = dead)
        self.health = 100          # 0-100 (player health)
        self.distance = 0          # km traveled
        self.inventory = {"water": 5, "bandage": 1}
        self.score = 0
        self.achievements = set()
        self.oasis_found = 0

class Camel:
    def __init__(self):
        self.stamina = 0           # 0-100 (100 = collapsed/exhausted)
        self.health = 100          # could be used by sandstorms/bandits
        self.sickness = False      # explicitly defined to avoid attribute errors

class Officers:
    def __init__(self, start_behind=20):
        # distance_behind: how many km behind the player (positive means behind)
        self.distance_behind = float(start_behind)

# ---------- Utility Functions ----------

def clamp(v, a, b):
    return max(a, min(b, v))

def pause_short():
    time.sleep(0.35)

def print_header(title):
    print("\n" + "="*len(title))
    print(title)
    print("="*len(title))

def save_game(state: dict):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"[Saved to {SAVE_FILE}]")
    except Exception as e:
        print("[Save failed]", e)

def load_game():
    if not os.path.exists(SAVE_FILE):
        print("[No save file found]")
        return None
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        print(f"[Loaded from {SAVE_FILE}]")
        return state
    except Exception as e:
        print("[Load failed]", e)
        return None

# ---------- Game Logic ----------

def choose_difficulty():
    print_header("Choose Difficulty")
    print("1) Easy   — Officers are slower. More forgiving events.")
    print("2) Normal — Balanced challenge.")
    print("3) Hard   — Officers are fast. Events harsher. Scores doubled.")
    while True:
        c = input("> ").strip()
        if c == "1":
            return "EASY", 0.08, 1.0
        if c == "2":
            return "NORMAL", 0.12, 1.5
        if c == "3":
            return "HARD", 0.16, 2.0
        print("Choose 1, 2 or 3.")

def ascii_map(player: Player, officers: Officers):
    # map shows player position and officers position on a 0..TOTAL_DISTANCE scale
    p_frac = clamp(player.distance / TOTAL_DISTANCE, 0.0, 1.0)
    o_position = player.distance - officers.distance_behind  # officers absolute position
    o_frac = clamp(o_position / TOTAL_DISTANCE, 0.0, 1.0)
    bar = ["-"] * MAP_WIDTH
    p_idx = min(MAP_WIDTH-1, int(p_frac * (MAP_WIDTH-1)))
    o_idx = min(MAP_WIDTH-1, int(o_frac * (MAP_WIDTH-1)))
    if o_idx == p_idx:
        bar[p_idx] = "X"  # very close or overlapping
    else:
        bar[p_idx] = "P"  # player
        bar[o_idx] = "O"  # officers
    return "[" + "".join(bar) + f"] {player.distance}/{TOTAL_DISTANCE} km"

def random_event(player: Player, camel: Camel, officers: Officers, difficulty: str):
    roll = random.randint(1, 100)
    chance_modifier = {"EASY": 0.8, "NORMAL": 1.0, "HARD": 1.2}[difficulty]
    # Oasis rare
    if roll <= int(3 * chance_modifier):
        player.oasis_found += 1
        player.thirst = 0
        camel.stamina = 0
        player.inventory["water"] = 5
        player.achievements.add("Found Oasis")
        return "✨ You found a hidden oasis! Water refilled & camel rested."
    # Supply cache
    if 4 <= roll <= int(8 * chance_modifier):
        found_water = random.randint(1, 3)
        player.inventory["water"] = player.inventory.get("water", 0) + found_water
        if random.random() < 0.3:
            player.inventory["bandage"] = player.inventory.get("bandage", 0) + 1
        return f"🔎 You discovered a small supply cache: +{found_water} water."
    # Sandstorm
    if 9 <= roll <= int(18 * chance_modifier):
        thirst_increase = random.randint(1, 2)
        camel_loss = random.randint(5, 20)
        player.thirst = clamp(player.thirst + thirst_increase, 0, 5)
        camel.stamina = clamp(camel.stamina + camel_loss, 0, 100)
        player.health = clamp(player.health - random.randint(0, 10), 0, 100)
        return "🌪️ A sandstorm lashes you — thirst and camel fatigue increase, and you suffer some damage."
    # Bandits
    if 19 <= roll <= int(27 * chance_modifier):
        lost = 0
        if player.inventory.get("water", 0) > 0 and random.random() < 0.7:
            lost = random.randint(1, min(3, player.inventory["water"]))
            player.inventory["water"] -= lost
        player.health = clamp(player.health - random.randint(5, 25), 0, 100)
        camel.health = clamp(camel.health - random.randint(0, 15), 0, 100)
        return f"🏴 Bandits attacked! You lose {lost} water and take damage."
    # Camel sickness
    if 28 <= roll <= int(32 * chance_modifier):
        camel.sickness = True
        camel.stamina = clamp(camel.stamina + random.randint(10, 25), 0, 100)
        return "🤒 Your camel looks ill — it will recover slowly unless you rest."
    return None

def calculate_score(player: Player, camel: Camel, difficulty_multiplier: float):
    base = player.distance * 10
    leftover = player.inventory.get("water", 0) * 20
    health_bonus = player.health
    camel_bonus = max(0, 100 - camel.stamina)
    oasis_bonus = player.oasis_found * 150
    achievement_bonus = len(player.achievements) * 100
    raw = base + leftover + health_bonus + camel_bonus + oasis_bonus + achievement_bonus
    return int(raw * difficulty_multiplier)

def check_achievements(player: Player, camel: Camel):
    if player.distance >= TOTAL_DISTANCE:
        player.achievements.add("Escape!")
    if player.inventory.get("water", 0) >= 10:
        player.achievements.add("Hoarder")
    if player.oasis_found >= 1:
        player.achievements.add("Oasis Seeker")
    if camel.stamina < 20:
        player.achievements.add("Tough Ride")
    if player.health >= 90 and camel.health >= 90:
        player.achievements.add("Pristine")

# ---------- Main Game Loop ----------

def play_game():
    print_header("Escape Across the Great Gobi — Ultimate Edition")
    # Allow load
    if os.path.exists(SAVE_FILE):
        print("Saved game exists. Load it? (y/N)")
        if input("> ").strip().lower() == "y":
            state = load_game()
            if state:
                # restore
                player = Player()
                # restore primitives and convert achievements list -> set
                player_state = state.get("player", {})
                player.thirst = player_state.get("thirst", 0)
                player.health = player_state.get("health", 100)
                player.distance = player_state.get("distance", 0)
                player.inventory = player_state.get("inventory", {"water": 5, "bandage": 1})
                player.score = player_state.get("score", 0)
                player.oasis_found = player_state.get("oasis_found", 0)
                # achievements
                ach_list = player_state.get("achievements", [])
                player.achievements = set(ach_list if isinstance(ach_list, list) else [])
                camel = Camel()
                camel_state = state.get("camel", {})
                camel.stamina = camel_state.get("stamina", 0)
                camel.health = camel_state.get("health", 100)
                camel.sickness = camel_state.get("sickness", False)
                officers = Officers()
                officers_state = state.get("officers", {})
                officers.distance_behind = float(officers_state.get("distance_behind", officers.distance_behind))
                difficulty = state.get("difficulty", "NORMAL")
                officer_speed = float(state.get("officer_speed", 0.12))
                diff_multiplier = float(state.get("diff_multiplier", 1.5))
                print("Game loaded. Resuming...")
                pause_short()
                return game_loop(player, camel, officers, difficulty, officer_speed, diff_multiplier)
    # New game
    difficulty, officer_speed, diff_multiplier = choose_difficulty()
    player = Player()
    camel = Camel()
    officers = Officers(start_behind=20 if difficulty == "NORMAL" else (25 if difficulty == "EASY" else 15))
    print("\nYour goal: cross 200 km while staying alive and keeping your camel walking.")
    pause_short()
    return game_loop(player, camel, officers, difficulty, officer_speed, diff_multiplier)

def game_loop(player: Player, camel: Camel, officers: Officers, difficulty, officer_speed, diff_multiplier):
    day = 1
    while True:
        print_header(f"Day {day} — Choose your action")
        print(ascii_map(player, officers))
        print(f"Player Health: {player.health}/100 | Thirst: {player.thirst}/5 | Water: {player.inventory.get('water',0)}")
        print(f"Camel Stamina (fatigue): {camel.stamina}% | Camel Health: {camel.health}/100")
        print(f"Officers are {int(officers.distance_behind)} km behind you.")
        print("\nActions:")
        print(" A) Drink water")
        print(" B) Move - Moderate")
        print(" C) Move - Full speed")
        print(" D) Rest (Camel recovers, officers close in)")
        print(" E) Use bandage (restore player health)")
        print(" F) Status and Inventory")
        print(" S) Save game")
        print(" Q) Quit (forfeit)")

        choice = input("> ").strip().upper()
        event_msg = None

        if choice == "Q":
            print("You gave up the journey. Game over.")
            player.score = calculate_score(player, camel, diff_multiplier)
            finalize(player, camel, diff_multiplier)
            return

        elif choice == "S":
            # save (serialize achievements to list)
            state = {
                "player": {
                    "thirst": player.thirst,
                    "health": player.health,
                    "distance": player.distance,
                    "inventory": player.inventory,
                    "score": player.score,
                    "oasis_found": player.oasis_found,
                    "achievements": list(player.achievements),
                },
                "camel": {
                    "stamina": camel.stamina,
                    "health": camel.health,
                    "sickness": camel.sickness,
                },
                "officers": {
                    "distance_behind": officers.distance_behind,
                },
                "difficulty": difficulty,
                "officer_speed": officer_speed,
                "diff_multiplier": diff_multiplier,
            }
            save_game(state)
            continue

        elif choice == "A":
            if player.inventory.get("water", 0) > 0:
                player.inventory["water"] -= 1
                player.thirst = 0
                print("You drink a bottle of water. Thirst reset.")
                player.achievements.add("Hydrated")
            else:
                print("You have no water left!")

        elif choice == "B":
            # moderate move
            travel = random.randint(5, 12)
            player.distance += travel
            player.thirst = clamp(player.thirst + 1, 0, 5)
            camel.stamina = clamp(camel.stamina + random.randint(5, 12), 0, 100)
            # officers advance based on officer_speed and randomness
            officers.distance_behind = clamp(
                officers.distance_behind - (travel * (officer_speed * random.uniform(0.8, 1.2))),
                -50, 1000
            )
            print(f"You travel {travel} km at a steady pace.")
            event_msg = random_event(player, camel, officers, difficulty)

        elif choice == "C":
            # full speed
            travel = random.randint(10, 20)
            player.distance += travel
            player.thirst = clamp(player.thirst + random.randint(1, 2), 0, 5)
            camel.stamina = clamp(camel.stamina + random.randint(10, 25), 0, 100)
            officers.distance_behind = clamp(
                officers.distance_behind - (travel * (officer_speed * random.uniform(0.4, 1.0))),
                -50, 1000
            )
            print(f"You dash full speed for {travel} km! The camel strains but you gain distance.")
            if random.random() < 0.6:
                event_msg = random_event(player, camel, officers, difficulty)

        elif choice == "D":
            # rest
            recovered = random.randint(10, 30)
            camel.stamina = clamp(camel.stamina - recovered, 0, 100)
            player.thirst = clamp(player.thirst + 1, 0, 5)
            officers.distance_behind = clamp(
                officers.distance_behind + random.randint(7, 14) * (officer_speed * 10),
                -50, 1000
            )
            print(f"You rest for the day. The camel recovers {recovered} stamina (fatigue reduced).")
            if random.random() < 0.12:
                event_msg = random_event(player, camel, officers, difficulty)

        elif choice == "E":
            if player.inventory.get("bandage", 0) > 0:
                player.inventory["bandage"] -= 1
                heal = random.randint(10, 30)
                player.health = clamp(player.health + heal, 0, 100)
                print(f"You use a bandage and stabilize yourself (+{heal} health).")
            else:
                print("No bandages available.")

        elif choice == "F":
            print("\n----- STATUS -----")
            print(f"Distance: {player.distance}/{TOTAL_DISTANCE} km")
            print(f"Player Health: {player.health}/100")
            print(f"Thirst: {player.thirst}/5")
            print(f"Camel: Stamina {camel.stamina}% | Health {camel.health}/100")
            print(f"Water: {player.inventory.get('water',0)} | Bandage: {player.inventory.get('bandage',0)}")
            print(f"Achievements: {', '.join(sorted(player.achievements)) if player.achievements else '(none)'}")
            input("\nPress Enter to continue...")
            continue

        else:
            print("Invalid choice.")
            continue

        # show random event message if any
        if event_msg:
            print("\n" + event_msg)
            pause_short()

        # check losing conditions
        if player.thirst >= 5:
            print("\n💀 You died of thirst. The desert claims you.")
            player.score = calculate_score(player, camel, diff_multiplier)
            finalize(player, camel, diff_multiplier)
            return

        if camel.stamina >= 100:
            print("\n💀 Your camel collapses from exhaustion. You are stranded.")
            player.score = calculate_score(player, camel, diff_multiplier)
            finalize(player, camel, diff_multiplier)
            return

        if officers.distance_behind <= 0:
            print("\n🚨 The officers have caught you! You are arrested.")
            player.score = calculate_score(player, camel, diff_multiplier)
            finalize(player, camel, diff_multiplier)
            return

        if player.health <= 0:
            print("\n💀 You succumbed to your wounds and the harsh desert.")
            player.score = calculate_score(player, camel, diff_multiplier)
            finalize(player, camel, diff_multiplier)
            return

        if player.distance >= TOTAL_DISTANCE:
            print("\n🏆 You crossed the Great Gobi and escaped to freedom!")
            player.score = calculate_score(player, camel, diff_multiplier)
            player.achievements.add("Escape!")
            finalize(player, camel, diff_multiplier)
            return

        check_achievements(player, camel)
        player.score = calculate_score(player, camel, diff_multiplier)
        day += 1
        pause_short()

def finalize(player: Player, camel: Camel, diff_multiplier: float):
    print_header("GAME OVER / SUMMARY")
    print(f"Distance traveled: {player.distance}/{TOTAL_DISTANCE} km")
    print(f"Final Player Health: {player.health}/100")
    print(f"Final Camel Stamina: {camel.stamina}% | Camel Health: {camel.health}/100")
    print(f"Water left: {player.inventory.get('water',0)}")
    print(f"Oases found: {player.oasis_found}")
    check_achievements(player, camel)
    print("\nAchievements unlocked:")
    if player.achievements:
        for a in sorted(player.achievements):
            print(" - " + a)
    else:
        print(" (none)")

    print(f"\nFinal Score: {player.score}")
    if os.path.exists(SAVE_FILE):
        print("\nWould you like to delete the save file? (y/N)")
        if input("> ").strip().lower() == "y":
            try:
                os.remove(SAVE_FILE)
                print("[Save file deleted]")
            except:
                print("[Failed to delete save file]")

    print("\nThanks for playing — try again on a harder difficulty to chase higher scores!")

# ---------- Entry Point ----------

if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        print("\nGame interrupted. Goodbye.")


