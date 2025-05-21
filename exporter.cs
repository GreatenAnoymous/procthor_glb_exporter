using UnityEngine;
using UnityEditor;
using System.IO;
using System.Collections;
using System.Collections.Generic; // For List<T>, Dictionary<K,V>, etc.
using UnityGLTF;
using Newtonsoft.Json.Linq;
using UnityStandardAssets.Characters.FirstPerson;
using Unity.EditorCoroutines.Editor; // Add this
public class ExportCleanSceneToGLTF
{
    [MenuItem("Tools/Export/Export Clean Scene to glb")]
    public static void ExportToGLTF()
    {
        string exportDir = "/home/ia/works/fbx/";
        string fileName = "scene";

        ExportHouseToGLB(exportDir, fileName);
    }


    private  static IEnumerator ExportAllHousesCoroutine()
    {
        string folderPath = Application.dataPath + "/Resources/rooms/";

        string exportPath = EditorUtility.OpenFolderPanel("Select Export Folder", "", "");
        if (string.IsNullOrEmpty(exportPath))
        {
            Debug.LogWarning("❌ Export folder not selected.");
            yield break;
        }

        string[] jsonFiles = Directory.GetFiles(folderPath, "*.json");

        foreach (var jsonFilePath in jsonFiles)
        {
            var debugInput = GameObject.FindObjectOfType<DebugInputField>();
            if (debugInput == null)
            {
                Debug.LogError("❌ Could not find DebugInputField in the scene.");
                continue;
            }

            string jsonName = Path.GetFileNameWithoutExtension(jsonFilePath);
            string createCmd = $"chp {jsonName}";

            Debug.Log($"📥 Creating house with command: {createCmd}");
            debugInput.Execute(createCmd);

            yield return new EditorWaitForSeconds(2.0f);

            ExportHouseToGLB(exportPath, jsonName);
            Debug.Log($"📤 Exported: {jsonName}");

            debugInput.Execute("des");

            yield return new EditorWaitForSeconds(1.0f);
            Debug.Log($"✅ Finished processing: {jsonFilePath}");
        }

        Debug.Log("🎉 All houses exported.");
    }


    public static void ExportHouseToGLB(string exportDir, string fileName)
    {
        if (!Directory.Exists(exportDir))
            Directory.CreateDirectory(exportDir);

        RemoveUnwantedObjects();

        List<Transform> exportRoots = new List<Transform>();
        GameObject[] rootObjects = UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
        foreach (GameObject root in rootObjects)
        {
            if (root.name == "Objects" || root.name == "Structure")
            {
                RemoveObjectsWithoutMesh(root.transform);
                exportRoots.Add(root.transform);
            }
        }

        if (exportRoots.Count == 0)
        {
            Debug.LogWarning("No valid root objects ('Objects' or 'Structure') found.");
            return;
        }

        var exportRootsArray = exportRoots.ToArray();
        GLTFSceneExporter.RetrieveTexturePathDelegate retrieveTexturePath = RetrieveTexturePath;

        var exporter = new GLTFSceneExporter(exportRootsArray, retrieveTexturePath);
        exporter.SaveGLB(exportDir, fileName);

        Debug.Log($"✅ Exported cleaned scene to: {Path.Combine(exportDir, fileName)}.glb");
    }

    private static string RetrieveTexturePath(Texture texture)
    {
        if (texture == null) return null;
        string path = AssetDatabase.GetAssetPath(texture);
        return string.IsNullOrEmpty(path) ? null : path;
    }

    private static void RemoveUnwantedObjects()
    {
        GameObject[] allObjects = Object.FindObjectsOfType<GameObject>();
        foreach (GameObject go in allObjects)
        {
            if (go.name.Contains("Ceiling") ||
                go.name.Contains("VisibilityPoint") ||
                go.name.Contains("Collider") ||
                go.name.Contains("Bounding") ||
                go.name.Contains("ReceptacleTriggerBox") ||
                go.name.Contains("Handle"))
            {
                Object.DestroyImmediate(go);
            }
        }
    }

    private static void RemoveObjectsWithoutMesh(Transform parent)
    {
        List<Transform> children = new List<Transform>();
        foreach (Transform child in parent)
            children.Add(child);

        foreach (Transform child in children)
        {
            RemoveObjectsWithoutMesh(child);

            bool hasMesh = child.GetComponent<MeshFilter>() != null || child.GetComponent<SkinnedMeshRenderer>() != null;

            if (!hasMesh && child.childCount == 0)
            {
                Object.DestroyImmediate(child.gameObject);
            }
        }
    }
    



    [MenuItem("Tools/Batch Export Houses to GLB")]
    public static void ExportAllHouses()
    {
        EditorCoroutineUtility.StartCoroutineOwnerless(ExportAllHousesCoroutine());
    }
}
