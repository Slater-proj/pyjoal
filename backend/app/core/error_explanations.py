"""
Error explanations for common tracker issues
"""

ERROR_EXPLANATIONS = {
    "signature_invalide": {
        "title": "Signature du torrent invalide",
        "description": "Le fichier .torrent n'est pas valide ou a été corrompu",
        "solutions": [
            "Re-téléchargez le fichier .torrent depuis le site officiel",
            "Vérifiez que le fichier n'est pas corrompu (taille > 0)",
            "Assurez-vous que le fichier .torrent provient bien du tracker"
        ],
        "category": "FILE_ERROR"
    },
    
    "droits_revoques": {
        "title": "Droits de téléchargement révoqués",
        "description": "Votre compte sur le tracker privé a des restrictions",
        "solutions": [
            "Contactez les administrateurs du tracker",
            "Vérifiez votre ratio sur le site",
            "Respectez les règles du tracker (Hit & Run, etc.)",
            "Attendez la fin d'une éventuelle sanction temporaire"
        ],
        "category": "ACCOUNT_ERROR",
        "note": "Même avec des droits de téléchargement révoqués, le seeding peut parfois fonctionner selon les trackers"
    },
    
    "not_authorized": {
        "title": "Non autorisé",
        "description": "Votre client n'est pas autorisé sur ce tracker",
        "solutions": [
            "Utilisez un client autorisé (vérifiez la liste sur le site)",
            "Mettez à jour la version de votre client",
            "Vérifiez les paramètres de votre client (User-Agent, etc.)"
        ],
        "category": "CLIENT_ERROR"
    },
    
    "torrent_not_found": {
        "title": "Torrent introuvable",
        "description": "Le torrent n'existe plus sur le tracker",
        "solutions": [
            "Le torrent a peut-être été supprimé du tracker",
            "Vérifiez sur le site si le torrent est toujours actif",
            "Supprimez ce torrent de PyJOAL"
        ],
        "category": "TRACKER_ERROR"
    }
}

def get_error_explanation(error_message: str) -> dict:
    """Get explanation for an error message"""
    error_lower = error_message.lower()
    
    if "signature" in error_lower and "invalide" in error_lower:
        return ERROR_EXPLANATIONS["signature_invalide"]
    elif "droits" in error_lower and "révoqués" in error_lower:
        return ERROR_EXPLANATIONS["droits_revoques"]
    elif "not authorized" in error_lower:
        return ERROR_EXPLANATIONS["not_authorized"]
    elif "not found" in error_lower or "introuvable" in error_lower:
        return ERROR_EXPLANATIONS["torrent_not_found"]
    else:
        return {
            "title": "Erreur inconnue",
            "description": error_message,
            "solutions": [
                "Vérifiez les logs pour plus de détails",
                "Redémarrez PyJOAL",
                "Vérifiez votre connexion internet"
            ],
            "category": "UNKNOWN_ERROR"
        }

def explain_seeding_with_revoked_rights() -> str:
    """Explain why seeding might work even with revoked download rights"""
    return """
    **Seeding avec droits révoqués :**
    
    C'est effectivement possible et normal selon les trackers :
    
    1. **Droits séparés** : Beaucoup de trackers privés séparent les droits de téléchargement et de partage
    2. **Encouragement du seeding** : Les trackers veulent que vous partagiez même si vous ne pouvez plus télécharger
    3. **Amélioration du ratio** : Seeder permet d'améliorer votre ratio pour récupérer vos droits
    4. **Politique du tracker** : Chaque tracker a sa propre politique
    
    **Que faire :**
    - Continuez à seeder pour améliorer votre ratio
    - Respectez les règles du tracker
    - Contactez les modérateurs si nécessaire
    """