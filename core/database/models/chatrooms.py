from core.database import MySQL
from core.database.models.agents import Agents
from core.database.models.chatroom_agent_relation import ChatroomAgentRelation
import math


class Chatrooms(MySQL):
    """
    A class that extends MySQL to manage operations on the {table_name} table.
    """

    table_name = "chatrooms"
    """
    Indicates whether the `chatrooms` table has an `update_time` column that tracks when a record was last updated.
    """
    have_updated_time = True

    def search_agent_id(self, agent_id: int):
        """
        Searches for an agent by its ID.

        This function queries the database to find an agent with the specified ID in the Agents table.
        It uses the `select_one` method from the `Agents` model to perform the search based on
        the provided agent ID. If an agent with the given ID exists, the function returns a dictionary
        indicating success. Otherwise, it indicates failure.

        :param agent_id: The ID of the agent to search for in the database.
        :type agent_id: int

        :return: A dictionary indicating the search result status.
                 - {'status': 1}: If the agent is found in the database.
                 - {'status': 0}: If the agent is not found in the database.
        :rtype: dict
        """
        agent_model = Agents()
        info = agent_model.select_one(
            columns=[
                'id',
            ],
            conditions=[
                {"column": "id", "value": agent_id},
            ]
        )
        if info is not None:
            return {'status': 1}
        else:
            return {'status': 0}

    def search_chatrooms_id(self, chatroom_id: int, user_id: int):
        """
        Retrieves information about a chat room by its ID.

        This function queries the database for a chat room with the specified ID.
        If the chat room exists, it returns a dictionary containing the chat room's
        maximum round, app ID, and a status code indicating success.

        :param chatroom_id: The ID of the chat room to search for.
        :return: A dictionary containing the chat room's information and a status code.
                 - If the chat room is found, the status code is 1.
                 - If the chat room is not found, the status code is 0.
        """
        info = self.select_one(
            columns=[
                'id', 'max_round', 'app_id', 'status', 'smart_selection'
            ],
            conditions=[
                {"column": "id", "value": chatroom_id},
                {"column": "user_id", "value": user_id},
                {"column": "status", "value": 1},
            ]
        )
        if info is not None:
            return {'status': 1, 'max_round': info['max_round'], 'app_id': info['app_id'], 'chatroom_status': info['status'], 'smart_selection': info['smart_selection']}
        else:
            return {'status': 0}

    def all_chat_room_list(self, page: int = 1, page_size: int = 10, uid: int = 0, name: str = ""):
        """
        Retrieves a list of chat rooms with pagination, filtering by user ID and chat room name.

        :param page: The page number for pagination.
        :param page_size: The number of items per page.
        :param uid: The ID of the user to filter chat rooms by.
        :param name: The name of the chat room to filter by.
        :return: A dictionary containing the list of chat rooms, total count, total pages, current page, and page size.
        """
        conditions = [
            {"column": "chatrooms.status", "value": 1},
            {"column": "apps.status", "value": 1},
            {"column": "apps.mode", "value": 5},
            {"column": "chatrooms.user_id", "value": uid},
        ]

        if name:
            conditions.append({"column": "apps.name", "op": "like", "value": "%" + name + "%"})

        total_count = self.select_one(
            aggregates={"id": "count"},
            joins=[
                ["left", "apps", "chatrooms.app_id = apps.id"],
            ],
            conditions=conditions,
        )["count_id"]

        list = self.select(
            columns=[
                "apps.name",
                "apps.description",
                "chatrooms.id as chatroom_id",
                "chatrooms.chat_status",
                "chatrooms.active",
                "chatrooms.status as chatroom_status",
                "chatrooms.smart_selection",
                "apps.id as app_id"
            ],
            joins=[
                ["left", "apps", "chatrooms.app_id = apps.id"]
            ],
            conditions=conditions,
            order_by="chatrooms.id DESC",
            limit=page_size,
            offset=(page - 1) * page_size
        )

        for chat_item in list:
            chat_item['agent_list'] = []
            agent_list = ChatroomAgentRelation().select(
                columns=["agent_id", "chatroom_id"],
                conditions=[
                    {"column": "chatroom_id", "value": chat_item['chatroom_id']}
                ],
                order_by="id DESC"
            )

            if agent_list:
                for agent_item in agent_list:
                    if agent_item['agent_id'] > 0:
                        chat_item['agent_list'].append(Agents().select_one(
                            columns=["apps.name", "apps.description", "agents.id AS agent_id", "agents.app_id", "apps.icon", "apps.icon_background", "agents.obligations"],
                            conditions=[
                                {"column": "id", "value": agent_item['agent_id']}
                            ],
                            joins=[
                                ["left", "apps", "apps.id = agents.app_id"],
                            ]
                        ))

        return {
            "list": list,
            "total_count": total_count,
            "total_pages": math.ceil(total_count / page_size),
            "page": page,
            "page_size": page_size
        }

    def recent_chatroom_list(self, chatroom_id: int, uid: int = 0):
        """
        Retrieves a list of the most recently active chat rooms for a given user, excluding a specific chat room.

        This function queries the database to find the most recently active chat rooms for the specified user,
        based on the 'last_run_time' from the 'app_runs' table. It excludes the chat room with the provided chatroom_id.
        It then retrieves the associated agents for each chat room in the list.

        Parameters:
        - chatroom_id (int): The ID of the chat room to exclude from the list. Required.
        - uid (int): The ID of the user to retrieve chat rooms for. Defaults to 0.

        Returns:
        - dict: A dictionary containing the list of recent chat rooms, with each chat room including its associated agents.
        """
        try:
            query = f"""
                SELECT apps.name, apps.description, chatrooms.id as chatroom_id, chatrooms.active, apps.id as app_id
                FROM chatrooms
                INNER JOIN apps ON chatrooms.app_id = apps.id
                INNER JOIN (
                    SELECT chatroom_id, MAX(created_time) as last_run_time
                    FROM app_runs
                    GROUP BY chatroom_id
                ) AS last_runs ON chatrooms.id = last_runs.chatroom_id
                WHERE chatrooms.status = 1 AND apps.status = 1 AND apps.mode = 5 AND chatrooms.user_id = {uid} AND chatrooms.id != {chatroom_id}
                ORDER BY last_run_time DESC
                LIMIT 5
            """
            list = self.execute_query(query)
            rows = list.mappings().all()
            chatrooms = [dict(row) for row in rows]
            for chatroom in chatrooms:
                chatroom_id = chatroom.get("chatroom_id")
                if chatroom_id:
                    agent_list = ChatroomAgentRelation().show_chatroom_agent(chatroom_id)
                    chatroom["agent_list"] = agent_list
            return {"list": chatrooms}
        except Exception as e:
            print(f"An error occurred: {e}")
            return {"list": []}