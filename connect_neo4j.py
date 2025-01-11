from neo4j import GraphDatabase # type: ignore

# Connect to Neo4j Database
uri = "bolt://localhost:7687"  # Replace with your Neo4j URI
username = "neo4j"
password = "your_pwd"  # Replace with your password
driver = GraphDatabase.driver(uri, auth=(username, password))

# Session management (to track logged in users)
current_user = None
def create_user_account(tx, name, password, age):
    name = name.strip()  # Remove leading/trailing spaces
    # Check if the user already exists
    query = """
    MATCH (p:Person {name: $name})
    RETURN p
    """
    result = tx.run(query, name=name)
    # If the user exists, print a message and prevent account creation
    if result.single() is not None:
        print(f"An account with the name '{name}' already exists. Please choose a different name.")
        return
    # If the user doesn't exist, create a new account
    query = """
    MERGE (p:Person {name: $name})
    SET p.age = $age, p.password = $password
    RETURN p
    """
    result = tx.run(query, name=name, password=password, age=age)
    print(f"Account for {name} created successfully.")
    return result.single()


# Function to log in a user
def log_in(tx, name, password):
    name = name.strip()  # Remove leading/trailing spaces
    query = """
    MATCH (p:Person {name: $name})
    RETURN p.password AS stored_password
    """
    result = tx.run(query, name=name)
    
    # Print the result to see what's returned from the query
    query_result = result.single()
    print("Query Result:", query_result)

    # Check if the result is None (no user found)
    if query_result is None:
        return False
    
    # If result is not None, proceed to access stored_password
    stored_password = query_result["stored_password"]
    
    # Debugging: Print stored password and the provided password
    print(f"Stored Password: {stored_password}, Provided Password: {password}")
    
    if stored_password == password:
        # print(f"Logged in successfully as {name}.")
        return True
    else:
        # print("Incorrect password. Please try again.")
        return False
    
# Function to follow another user
def follow_user(tx, current_user, target_name):
    query = """
    MATCH (p:Person {name: $target_name})
    RETURN p
    """
    result = tx.run(query, target_name=target_name)
    if result.single() is None:
        print(f"User '{target_name}' does not exist. Cannot follow.")
        return
    
    # Proceed with the follow logic (assuming unidirectional 'FOLLOWS' relationship)
    query = """
    MATCH (a:Person {name: $current_user}), (b:Person {name: $target_name})
    MERGE (a)-[:FOLLOWS]->(b)
    """
    tx.run(query, current_user=current_user, target_name=target_name)
    print(f"Now following {target_name}.")
    return

# Function to send a friend request
def send_friend_request(tx, current_user_name, target_name):
    current_user_name = current_user_name.strip()
    target_name = target_name.strip()
    query = """
    MATCH (p:Person {name: $target_name})
    RETURN p
    """
    result = tx.run(query, target_name=target_name)
    if result.single() is None:
        print(f"User '{target_name}' does not exist.")
        return
    
    query = """
    MATCH (a:Person {name: $current_user_name})-[:FRIENDS_WITH]-(b:Person {name: $target_name})
    RETURN b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    if result.single() is not None:
        print(f"You are already friends with '{target_name}'.")
        return
    
    query = """
    MATCH (a:Person {name: $current_user_name}), (b:Person {name: $target_name})
    MERGE (a)-[:SENT_REQUEST]->(b)
    RETURN a, b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    print(f"Friend request sent to {target_name}.")
    return

# Function to see incoming friend requests
def see_friend_requests(tx, receiver_name):
    query = """
    MATCH (receiver:Person {name: $receiver_name})<-[:SENT_REQUEST]-(sender)
    RETURN sender.name AS request_sender
    """
    result = tx.run(query, receiver_name=receiver_name)
    return [record["request_sender"] for record in result]

# Function to accept friend request
def accept_friend_request(tx, current_user_name, target_name):
    current_user_name = current_user_name.strip()
    target_name = target_name.strip()
    query = """
    MATCH (p:Person {name: $target_name})
    RETURN p
    """
    result = tx.run(query, target_name=target_name)
    if result.single() is None:
        print(f"User '{target_name}' does not exist.")
        return False
    
    query = """
    MATCH (a:Person {name: $current_user_name})-[:SENT_REQUEST]->(b:Person {name: $target_name})
    RETURN b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    if result.single() is None:
        print(f"No friend request from '{target_name}' to accept.")
        return
    
    query = """
    MATCH (a:Person {name: $current_user_name}), (b:Person {name: $target_name})
    MERGE (a)-[:FRIENDS_WITH]-(b)
    DELETE (a)-[:SENT_REQUEST]->(b)  # Remove the friend request
    RETURN a, b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    print(f"'{current_user_name}' and '{target_name}' are now friends.")
    return

# Function to ignore friend request
def ignore_friend_request(tx, current_user_name, target_name):
    current_user_name = current_user_name.strip()
    target_name = target_name.strip()
    query = """
    MATCH (p:Person {name: $target_name})
    RETURN p
    """
    result = tx.run(query, target_name=target_name)
    if result.single() is None:
        print(f"User '{target_name}' does not exist.")
        return
    query = """
    MATCH (a:Person {name: $current_user_name})-[:SENT_REQUEST]->(b:Person {name: $target_name})
    RETURN b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    if result.single() is None:
        print(f"No friend request from '{target_name}' to ignore.")
        return
    query = """
    MATCH (a:Person {name: $current_user_name})-[r:SENT_REQUEST]->(b:Person {name: $target_name})
    DELETE r
    RETURN a, b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    print(f"Friend request from '{target_name}' ignored.")
    return

# Function to suggest friends based on mutual friends
def suggest_friends(tx, user_name):
    query = """
    MATCH (p1:Person {name: $user_name})-[:FRIENDS_WITH]-(friend)-[:FRIENDS_WITH]-(suggested_friend)
    WHERE NOT (p1)-[:FRIENDS_WITH]-(suggested_friend)
    RETURN suggested_friend.name AS suggestion
    """
    result = tx.run(query, user_name=user_name)
    suggestions = [record["suggestion"] for record in result]
    return suggestions

# Function to send a message to a friend
def send_message(tx, current_user_name, target_name, message):
    current_user_name = current_user_name.strip()
    target_name = target_name.strip()
    query = """
    MATCH (p:Person {name: $target_name})
    RETURN p
    """
    result = tx.run(query, target_name=target_name)
    if result.single() is None:
        print(f"User '{target_name}' does not exist.")
        return
    query = """
    MATCH (a:Person {name: $current_user_name})-[:FRIENDS_WITH]-(b:Person {name: $target_name})
    RETURN b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    if result.single() is None:
        print(f"You are not friends with '{target_name}', cannot send message.")
        return
    query = """
    MATCH (a:Person {name: $current_user_name}), (b:Person {name: $target_name})
    MERGE (a)-[:SENT_MESSAGE]->(b)
    SET b.message = $message
    RETURN a, b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name, message=message)
    print(f"Message sent to {target_name}.")
    return

# Function to see messages from friends
def see_messages(tx, user_name):
    query = """
    MATCH (user:Person {name: $user_name})<-[:TO]-(message:Message)-[:SENT_MESSAGE]->(sender)
    RETURN sender.name AS sender, message.content AS content, message.timestamp AS timestamp
    """
    result = tx.run(query, user_name=user_name)
    messages = [{"sender": record["sender"], "content": record["content"], "timestamp": record["timestamp"]} for record in result]
    return messages

# User interaction function with session management
def user_interaction():
    global current_user
    print("Welcome to the Social Media Network!")

    while True:
        if current_user is None:
            action = input("\nChoose an action (create_account, log_in, exit): ").lower()
            if action == "create_account":
                name = input("Enter your name: ")
                password = input("Enter your password: ")
                age = int(input("Enter your age: "))
                with driver.session() as session:
                    session.execute_write(create_user_account, name, password, age)
                    # print(f"Account created for {name}.")
            elif action == "log_in":
                name = input("Enter your name: ")
                password = input("Enter your password: ")
                with driver.session() as session:
                    if session.execute_read(log_in, name, password):
                        current_user = name
                        print(f"Logged in as {current_user}.")
                    else:
                        print("Invalid credentials. Please try again.")
            elif action == "exit":
                print("Exiting the system. Goodbye!")
                break
            else:
                print("Invalid action. Please choose a valid action.")
        else:
            action = input("\nLogged in as {0}. Choose an action (follow, send_friend_request, see_friend_requests, accept_request, ignore_request, suggest_friends, remove_friend, see_friend_list, message_friend, see_messages, sign_out): ".format(current_user)).lower()
            
            with driver.session() as session:
                if action == "follow":
                    followee = input("Enter the name of the person you want to follow: ")
                    session.execute_write(follow_user, current_user, followee)
                    # print(f"{current_user} is now following {followee}.")
                elif action == "send_friend_request":
                    friend_name = input("Enter the name of the person you want to send a friend request to: ")
                    session.execute_write(send_friend_request, current_user, friend_name)
                    # print(f"Friend request sent to {friend_name}.")
                elif action == "see_friend_requests":
                    requests = session.execute_read(see_friend_requests, current_user)
                    if requests:
                        print("Friend requests:", ", ".join(requests))
                    else:
                        print("No friend requests.")
                elif action == "accept_request":
                    sender = input("Enter the name of the person whose friend request you want to accept: ")
                    session.execute_write(accept_friend_request, sender, current_user)
                    # print(f"Friend request from {sender} accepted.")
                elif action == "ignore_request":
                    sender = input("Enter the name of the person whose friend request you want to ignore: ")
                    session.execute_write(ignore_friend_request, sender, current_user)
                    # print(f"Friend request from {sender} ignored.")
                elif action == "suggest_friends":
                    suggestions = session.execute_read(suggest_friends, current_user)
                    if suggestions:
                        print("Friend suggestions:", ", ".join(suggestions))
                    else:
                        print("No suggestions available.")
                elif action == "remove_friend":
                    friend_name = input("Enter the name of the friend you want to remove: ")
                    session.execute_write(remove_friend, current_user, friend_name)
                    print(f"{friend_name} has been removed from your friends list.")
                elif action == "see_friend_list":
                    query = """
                    MATCH (p:Person {name: $name})-[:FRIENDS_WITH]-(friend)
                    RETURN friend.name AS friend
                    """
                    result = session.run(query, name=current_user)
                    friends = [record["friend"] for record in result]
                    print("Your friends:", ", ".join(friends))
                elif action == "message_friend":
                    friend_name = input("Enter the name of the friend you want to message: ")
                    message = input("Enter your message: ")
                    session.execute_write(send_message, current_user, friend_name, message)
                    # print(f"Message sent to {friend_name}.")
                elif action == "see_messages":
                    messages = session.execute_read(see_messages, current_user)
                    if messages:
                        for message in messages:
                            print(f"From {message['sender']} at {message['timestamp']}: {message['content']}")
                    else:
                        print("No messages.")
                elif action == "sign_out":
                    current_user = None
                    print("You have been signed out.")
                else:
                    print("Invalid action. Please choose a valid action.")
user_interaction()