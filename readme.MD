# The Traitors

### **Game description**

All players joining the game are randomly assigned (see variants) as a traitor or faithful. A minimum of 3 players are required.

The number of traitors assigned will be fewer than the number of traitors. Proportion to be confirmed by approximately 1/3.

Once the game starts an administrator starts the game. At that point all players have an amount of time (say 5 minutes) to vote to eliminate one or more traitors. 

Players will have a chat function to discuss who they are thinking of eliminating and why. They don’t need to use this.

Players vote by selecting one or more players from a voting list. The number of votes each player can make will be decided in the game configuration. Players will have to make that many votes, they cannot abstain but they can select ‘no traitors’. If they fail to vote by the voting deadline they will be removed from the game. Players will be able to see who has voted for whom from the voting list. There will be a refresh button to update the list. For traitors only, the voting list will identify who the traitors are.

Once all players have voted, the round will finish. The player or players with the most votes will be eliminated. The eliminated players will be confirmed in the chat. They will be unable to vote in subsequent rounds and there name will no longer appear in the voting list however they will still be able to participate in the chat.

? The traitors votes will count in the public elimination but will also count in a secret count and elimination. The elimination for the secret vote will occur at the round midpoint. The eliminated players will be confirmed in the chat.

The game continues until all players have clicked ‘no traitors’. If there are any traitors left in the game at that point they will win. If there are no traitors, the faithful will win.

[round time] = [length of game] / ([total number of players] / 2 x [number eliminated per round] )


**Variants**

The assignment of traitors could not be random and instead be based on user's names or some other system that players 
would be able to understand if they read the code from the git respository, which would be shared. In this way, more
than one round could be player.

More than one game could be enabled. Admins could set up games and users could then join.


### **Game design/detail**

#### home/index page:

Welcomes players and summarises the number of players who have joined
Text box to enter user name and button to join
When the join button is clicked the users will be added to the join wait list.
When an administrator joins the game, the game will start.

#### Game page

The game page will present a checkbox list of players in the game which is the voting board. Once a player has voted for by clicking a player or players they won’t be able to change their vote. The number of players eliminated each round will be a game setting. Cast votes will show to all players against the players name. 

The page will display a timer showing the round time.

Traitors will be able to see who the other traitors are by a check mark next to their name.

A chat function will be provided to enable players to communicate with each other.

Once all votes are cast or the round time is reached, the result of the elimination will be added to the chat.

If all players have not voted to end the game, the timer will reset and a new round will start 	and the voting board will be cleared.

At the midpoint of round, the tallied votes from the traitors will eliminate additional players. The number of players eliminated will be the same as the number eliminated in the public vote. If the traitors collectively vote for fewer players than the number to be eliminated, a faithful will be randomly selected.