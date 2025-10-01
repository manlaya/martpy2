!> @brief Fichier Configuration de MARTHE
!>
!> version pour martpy : noms des objets, fichier et variables editables
program martconf
    
    ! --- From libmarthe:
    use NBFICMAR
    use MARLIBFI
    use SMARTCOM
    use MARLIBFI    ! Libellés des Fichiers, IFICHI, IFICH_GRID etc.
    use OBJETS_MARTH, only : AFFECT_OBJET_MART, OBJETMART
    
    implicit none
    
    ! --- Locals
    integer :: IERNEW, KONT, IFI, IS_FILE
    character(len=23) :: FILENAME_CONFIG
    character(len=1), parameter :: TAB = CHAR(9)

    FILENAME_CONFIG = "marthe_variables.csv"

    !     =================================
    !      Initialisation OBJETS et VERTIT
    !     =================================
    call AFFECT_OBJET_MART()
    !     =================================================
    !      * Initialisation des valeurs de VERTIT
    !     =================================================
    call LOAD_VERTIT()
    IOUT = 3
      
    call OPENEW(IOUT, FILENAME_CONFIG, IERNEW, 1)
      
    ! write (IOUT, "(9(A,';'))") &
    write (IOUT, "(A)") &
        "id"            //TAB // &
        "is_grid"       //TAB // &
        "code_var_fr"   //TAB // &
        "code_var_en"   //TAB // &
        "code_abb"      //TAB // &
        "ext"           //TAB // &
        "surface_field" //TAB // &
        "descr"         //TAB // &
        "is_file"
    
    KONT = 0
    ! * À partir de NBFICH+ 1 => NBFIC3 : Ce sont des Objets qui ne sont pas des Fichiers :
    !          Ex: Rabattements, Valeur par Zone Climatique
    !          , Variable Éditable etc.
    !  voir Marthe/src/modumar_objets_marth.f90 L731
    ! on rajoute donc +121 dans la boucle, et une variable is_file ; puis on fera les nbfic3
    do IFI=1,NBFICH+121
        IS_FILE = IFICHI(IFI)
        ! if (ifi == 211) is_file = 0  ! c'est perhisto, TMP
        !        ===========================================================================
        !         On conserve les fichiers IFICHI() = -1
        !         Ce sont des fichiers (Grilles_Marthe) Temporaires non utilisés par MARTHE
        !         Mais utilisés par WinMarthe (comme "Travail" / Buffers)
        !        ===========================================================================
        !        ==========================================================
        !         les fichiers temporaires avaient un profil 1 (au lieu 0)
        !         Par sécurité => On met 0
        !        ==========================================================
        if (IFICHI(IFI) == -1) then 
            OBJETMART(IFI)%MASQ_FICH(1:3) = 0
            IS_FILE = 0
        end if
        ! SELECT CASE ( IFICHI(IFI) )
        ! CASE (:-1 , 1:)
            KONT = KONT + 1
!           ===================================
!            Édition du fichier
!           ===================================
            write ( &
                IOUT, "(I3, A, I1,A, A, A, A, A, A, A, A, A, I1, A, A, A, I1)" &
            ) &
                KONT,                      TAB, &
                IFICH_GRID(IFI),           TAB, &
                trim(CODTIT_13(IFI)) ,     TAB, &
                trim(CODTIT_13_TRAD(IFI)), TAB, &
                trim(CODTIT(IFI)),         TAB, &
                trim(EXTENS(IFI)),         TAB, &
                OBJETMART(IFI)%I_SURF,     TAB, &
                trim(VERTIT(IFI)),         TAB, &
                IS_FILE
        ! ici on garde aussi les 0 (ce qui a l'air d'être déjà une variable is_file en fait
        ! on vire donc le case sinon il ne se passe rien
        ! CASE (0)
            ! CYCLE
        ! END SELECT
    enddo

end program martconf
