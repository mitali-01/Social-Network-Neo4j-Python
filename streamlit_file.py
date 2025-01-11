import streamlit as st # type: ignore
from neo4j import GraphDatabase # type: ignore

uri = "bolt://localhost:7687"  # Replace with your Neo4j URI
username = "neo4j"
password = "your_pwd"  # Replace with your password
driver = GraphDatabase.driver(uri, auth=(username, password))

current_user = None

def create_user_account(tx, name, password, age):
    name = name.strip()
    query = """
    MATCH (p:Person {name: $name})
    RETURN p
    """
    result = tx.run(query, name=name)
    if result.single() is not None:
        return "An account with this name already exists!"
    if age < 13:
        return "Age must be 13 or older!"
    query = """
    MERGE (p:Person {name: $name})
    SET p.age = $age, p.password = $password
    RETURN p
    """
    result = tx.run(query, name=name, password=password, age=age)
    return f"Account for {name} created successfully!"

def log_in(tx, name, password):
    query = f"MATCH (p:Person {{name: '{name}', password: '{password}'}}) RETURN p"
    with driver.session() as session:
        result = session.run(query)
        if result.single():
            return f"Logged in as {name}"
        else:
            return "Invalid username or password"

def follow_user(tx, current_user, target_name):
    # Check if the target user exists
    query = "MATCH (p:Person {name: $target_name}) RETURN p"
    result = tx.run(query, target_name=target_name)
    if result.single() is None:
        return f"User '{target_name}' does not exist."
    
    # Check if the current user is already following the target user or is friends with them
    query = """
    MATCH (a:Person {name: $current_user})-[:FOLLOWS]->(b:Person {name: $target_name})
    RETURN b
    """
    result = tx.run(query, current_user=current_user, target_name=target_name)
    if result.single() is not None:
        return f"You are already following {target_name}."
    
    # Check if the current user is friends with the target user
    query = """
    MATCH (a:Person {name: $current_user})-[:FRIENDS_WITH]-(b:Person {name: $target_name})
    RETURN b
    """
    result = tx.run(query, current_user=current_user, target_name=target_name)
    if result.single() is not None:
        return f"You are already friends with {target_name}, no need to follow them."

    # Proceed to follow the target user
    query = """
    MATCH (a:Person {name: $current_user}), (b:Person {name: $target_name})
    MERGE (a)-[:FOLLOWS]->(b)
    """
    tx.run(query, current_user=current_user, target_name=target_name)
    return f"Now following {target_name}."

def send_message(tx, current_user_name, target_name, message):
    query = "MATCH (p:Person {name: $target_name}) RETURN p"
    result = tx.run(query, target_name=target_name)
    if result.single() is None:
        return f"User '{target_name}' does not exist."
    
    query = """
    MATCH (a:Person {name: $current_user_name})-[:FRIENDS_WITH]-(b:Person {name: $target_name})
    RETURN b
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name)
    if result.single() is None:
        return f"You are not friends with '{target_name}', cannot send message."
    
    # Create a new message node and relationships
    query = """
    MATCH (a:Person {name: $current_user_name}), (b:Person {name: $target_name})
    CREATE (m:Message {content: $message, timestamp: datetime()})
    CREATE (a)-[:SENT_MESSAGE]->(m)
    CREATE (m)-[:TO]->(b)
    RETURN m
    """
    result = tx.run(query, current_user_name=current_user_name, target_name=target_name, message=message)
    return f"Message sent to {target_name}."


def see_messages(tx, user_name):
    print(f"Fetching messages for: {user_name}")  # Debugging line
    query = """
    MATCH (user:Person {name: $user_name})<-[:TO]-(message:Message)<-[:SENT_MESSAGE]-(sender)
    RETURN sender.name AS sender, message.content AS content, message.timestamp AS timestamp
    """
    result = tx.run(query, user_name=user_name)
    messages = [{"sender": record["sender"], "content": record["content"], "timestamp": record["timestamp"]} for record in result]
    return messages



def view_friends(tx, user_name):
    query = """
    MATCH (p:Person {name: $name})-[:FRIENDS_WITH]-(friend)
    RETURN friend.name AS friend
    """
    result = tx.run(query, name=user_name)
    friends = [record["friend"] for record in result]
    return friends

# Function to send a friend request

# Function to see all friend requests
def see_friend_requests(tx, current_user):
    query = """
    MATCH (a:Person {name: $current_user})<-[:FRIEND_REQUEST]-(b:Person)
    RETURN b.name AS sender
    """
    result = tx.run(query, current_user=current_user)
    return [{"sender": record["sender"]} for record in result]  # Return a list of users who sent requests

# Function to accept a friend request
def send_friend_request(tx, current_user, recipient_name):
    query = """
    MATCH (a:Person {name: $current_user}), (b:Person {name: $recipient_name})
    WHERE NOT (a)-[:FRIEND_REQUEST]->(b)
    CREATE (a)-[:FRIEND_REQUEST]->(b)
    RETURN 'Friend request sent' AS message
    """
    result = tx.run(query, current_user=current_user, recipient_name=recipient_name)
    return result.single()[0]  # Returns 'Friend request sent'

# Accept Friend Request
def accept_friend_request(tx, current_user, sender_name):
    query = """
    MATCH (a:Person {name: $current_user})<-[:FRIEND_REQUEST]-(b:Person {name: $sender_name})
    MERGE (a)-[:FRIENDS_WITH]->(b)
    WITH a, b
    MATCH (b)-[r:FRIEND_REQUEST]->(a)
    DELETE r
    RETURN 'Friend request accepted' AS message
    """
    result = tx.run(query, current_user=current_user, sender_name=sender_name)
    return result.single()[0] # Returns 'Friend request accepted'

# Ignore Friend Request
def ignore_friend_request(tx, current_user, sender_name):
    query = """
    MATCH (a:Person {name: $current_user})<-[:FRIEND_REQUEST]-(b:Person {name: $sender_name})
    WITH a, b
    MATCH (b)-[r:FRIEND_REQUEST]->(a)
    DELETE r
    RETURN 'Friend request ignored' AS message
    """
    result = tx.run(query, current_user=current_user, sender_name=sender_name)
    return result.single()[0]  # Returns 'Friend request ignored'

def suggest_friends(tx, current_user):
    query = """
    MATCH (a:Person {name: $current_user})-[:FRIENDS_WITH]-(friend)-[:FRIENDS_WITH]-(suggested_friend)
    WHERE NOT (a)-[:FRIENDS_WITH]-(suggested_friend) AND suggested_friend <> a
    RETURN DISTINCT suggested_friend.name AS suggested_friend
    """
    result = tx.run(query, current_user=current_user)
    return [record["suggested_friend"] for record in result]
    
def main():
    # Initialize current_user in session_state if not already set
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    # st.write(f"Current user (session_state): {st.session_state.current_user}")  # Debugging line

    st.title("Social Media Network")

    if st.session_state.current_user is None:
        # Create Account or Log In
        st.subheader("Create Account / Log In")
        
        action = st.radio("Choose an action", ("Create Account", "Log In"))
        # st.write(f"Action selected: {action}")  # Debugging line

        if action == "Create Account":
            name = st.text_input("Enter your name")
            password = st.text_input("Enter your password", type="password")
            age = st.number_input("Enter your age", min_value=13)
            
            if st.button("Create Account"):
                with driver.session() as session:
                    response = session.execute_write(create_user_account, name, password, age)
                    st.write(response)
                    
        elif action == "Log In":
            name = st.text_input("Enter your name")
            password = st.text_input("Enter your password", type="password")
            
            if st.button("Log In"):
                with driver.session() as session:
                    response = session.execute_write(log_in, name, password)
                    # st.write(f"Login response: {response}")  # Debugging line
                    
                    # Only set current_user if login was successful
                    if "Logged in as" in response:
                        st.session_state.current_user = name  # Update session state only if login is successful
                        st.write(f"Current user (after login): {st.session_state.current_user}")  # Debugging line
                        st.rerun()  # Force a rerun to update the page
                    else:
                        st.write("Login failed. Please check your credentials.")  # Error message on failed login

    else:
        # Logged in screen
        st.subheader(f"Welcome, {st.session_state.current_user}!")
        
        action = st.radio("Choose an action", ("Follow", "Send Message", "See Messages", "View Friends List", "Send Friend Request", "See Friend Requests", "Suggest Friends"))
        # st.write(f"Action selected: {action}")  # Debugging line

        if action == "Follow":
            query = "MATCH (p:Person) RETURN p.name AS name"
            with driver.session() as session:
                result = session.run(query)
                user_list = [record["name"] for record in result if record["name"] != st.session_state.current_user]

            target_name = st.selectbox("Choose a user to follow", user_list)
            if st.button("Follow"):
                with driver.session() as session:
                    response = session.execute_write(follow_user, st.session_state.current_user, target_name)
                    st.write(response)
                    
        elif action == "Send Message":
            friend_name = st.selectbox("Choose a friend", view_friends(driver.session(), st.session_state.current_user))
            message = st.text_area("Enter your message")
            if st.button("Send Message"):
                with driver.session() as session:
                    response = session.execute_write(send_message, st.session_state.current_user, friend_name, message)
                    st.write(response)
                    
        elif action == "See Messages":
            response = see_messages(driver.session(), st.session_state.current_user)
            if isinstance(response, str):
                st.write(response)
            else:
                for msg in response:
                    st.write(f"From: {msg['sender']} | Message: {msg['content']} | Timestamp: {msg['timestamp']}")
                    
        elif action == "View Friends List":
            friends = view_friends(driver.session(), st.session_state.current_user)
            if friends:
                for friend in friends:
                    st.write(friend)
            else:
                st.write("No friends yet.")
        
        elif action == "Suggest Friends":
            with driver.session() as session:
                suggestions = session.execute_read(suggest_friends, st.session_state.current_user)
            if suggestions:
                st.write("Friend Suggestions:")
                for suggestion in suggestions:
                    st.write(suggestion)
            else:
                st.write("No suggestions available.")

        elif action == "Send Friend Request":
            query = "MATCH (p:Person) RETURN p.name AS name"
            with driver.session() as session:
                result = session.run(query)
                user_list = [record["name"] for record in result if record["name"] != st.session_state.current_user]

            target_name = st.selectbox("Choose a user to send a friend request", user_list)
            if st.button("Send Friend Request"):
                with driver.session() as session:
                    response = session.execute_write(send_friend_request, st.session_state.current_user, target_name)
                    st.write(response)
        
        elif action == "See Friend Requests":
            friend_requests = see_friend_requests(driver.session(), st.session_state.current_user)
            if friend_requests:
                for request in friend_requests:
                    st.write(f"Friend request from: {request['sender']}")
                    accept_button = st.button(f"Accept {request['sender']}", key=f"accept_{request['sender']}")
                    ignore_button = st.button(f"Ignore {request['sender']}", key=f"ignore_{request['sender']}")
                    
                    if accept_button:
                        with driver.session() as session:
                            response = session.execute_write(accept_friend_request, st.session_state.current_user, request['sender'])
                            st.write(response)
                        st.rerun()

                    if ignore_button:
                        with driver.session() as session:
                            response = session.execute_write(ignore_friend_request, st.session_state.current_user, request['sender'])
                            st.write(response)
                        st.rerun()

            else:
                st.write("No friend requests.")

        if st.button("Sign Out"):
            del st.session_state['current_user']
            st.rerun()

if __name__ == "__main__":
    main()