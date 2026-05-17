"""
VUT Headless SDK — ROS Publisher (stub)
Publishes tracker poses as ROS geometry_msgs/PoseStamped topics.

Topic per tracker: /vut/{serial}/pose

Status: stub — ROS integration planned for v0.3
Requires: ROS2 + rclpy + geometry_msgs

Run: python ros_publisher.py
"""
# ROS2 implementation stub
# Full implementation coming in v0.3
#
# This will publish to:
#   /vut/{serial}/pose  (geometry_msgs/PoseStamped)
#   /vut/meta           (std_msgs/String — tracker count, fps)
#
# Track progress: github.com/nandunabey/VUT-Headless-SDK

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import PoseStamped
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False
    print("ROS2/rclpy not found.")
    print("Install ROS2: https://docs.ros.org/en/humble/")
    print("ROS publisher coming in VUT SDK v0.3")
    exit(1)

import asyncio, websockets, json

WS_URL = "ws://localhost:8765"

class VUTPosePublisher(Node):
    def __init__(self):
        super().__init__("vut_pose_publisher")
        self.publishers_ = {}
        self.get_logger().info("VUT Pose Publisher started")
        self.get_logger().info(f"Connecting to {WS_URL}")

    def get_publisher(self, serial):
        if serial not in self.publishers_:
            topic = f"/vut/{serial.replace('-','_')}/pose"
            self.publishers_[serial] = self.create_publisher(
                PoseStamped, topic, 10)
            self.get_logger().info(f"Publishing: {topic}")
        return self.publishers_[serial]

    def publish_pose(self, serial, pose):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "vut_world"
        msg.pose.position.x = pose["position"]["x"]
        msg.pose.position.y = pose["position"]["y"]
        msg.pose.position.z = pose["position"]["z"]
        msg.pose.orientation.w = pose["rotation"]["w"]
        msg.pose.orientation.x = pose["rotation"]["x"]
        msg.pose.orientation.y = pose["rotation"]["y"]
        msg.pose.orientation.z = pose["rotation"]["z"]
        self.get_publisher(serial).publish(msg)

async def stream(node):
    async with websockets.connect(WS_URL) as ws:
        async for message in ws:
            data = json.loads(message)
            for serial, pose in data.items():
                if serial == "meta":
                    continue
                node.publish_pose(serial, pose)

def main():
    rclpy.init()
    node = VUTPosePublisher()
    asyncio.run(stream(node))
    rclpy.shutdown()

if __name__ == "__main__":
    main()
