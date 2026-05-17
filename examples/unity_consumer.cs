/*
 * VUT Headless SDK — Unity Consumer
 * Attach to a GameObject. Connects to tracker daemon
 * and updates Transform positions in real time.
 * Requires: NativeWebSocket (https://github.com/endel/NativeWebSocket)
 * or Unity WebSocket package of your choice.
 */
using System;
using System.Collections.Generic;
using UnityEngine;
using NativeWebSocket;

public class VUTConsumer : MonoBehaviour
{
    [Header("VUT SDK")]
    public string wsUrl = "ws://localhost:8765";

    // Map serial numbers to GameObjects
    public SerialToObject[] trackerMap;

    [Serializable]
    public struct SerialToObject
    {
        public string serial;
        public GameObject target;
    }

    private WebSocket ws;
    private Dictionary<string, GameObject> map;

    async void Start()
    {
        map = new Dictionary<string, GameObject>();
        foreach (var entry in trackerMap)
            map[entry.serial] = entry.target;

        ws = new WebSocket(wsUrl);

        ws.OnMessage += (bytes) =>
        {
            var json = System.Text.Encoding.UTF8.GetString(bytes);
            var data = JsonUtility.FromJson<PoseFrame>(json);
            // Parse and apply poses
            // See full example in docs/
        };

        await ws.Connect();
    }

    void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        ws?.DispatchMessageQueue();
#endif
    }

    async void OnDestroy()
    {
        if (ws != null)
            await ws.Close();
    }
}
/*
 * Note: Unity JSON parsing requires concrete classes.
 * See examples/unity_full/ for complete implementation
 * with proper pose deserialization.
 */
